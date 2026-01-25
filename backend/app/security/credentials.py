from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as EncodingError
from hashlib import scrypt, sha256
from hmac import compare_digest
from secrets import token_bytes, token_urlsafe
from threading import BoundedSemaphore

from app.services.errors import AuthenticationBusy

_SLOTS = BoundedSemaphore(2)
_DUMMY_RECORD = bytes(48)


def _derive(password: str, salt: bytes) -> bytes:
    if not _SLOTS.acquire(blocking=False):
        raise AuthenticationBusy()
    try:
        return scrypt(password.encode(), salt=salt, n=2 ** 17, r=8, p=1, dklen=32, maxmem=160 * 1024 * 1024)
    finally:
        _SLOTS.release()


def password_hash(password: str) -> str:
    salt = token_bytes(16)
    return "scrypt-v1$" + urlsafe_b64encode(salt + _derive(password, salt)).decode()


def password_valid(password: str, hashed: str | None) -> bool:
    try:
        stored = urlsafe_b64decode(hashed.removeprefix("scrypt-v1$")) if hashed and hashed.startswith("scrypt-v1$") else b""
    except (EncodingError, ValueError):
        stored = b""
    valid_format = len(stored) == 48
    record = stored if valid_format else _DUMMY_RECORD
    return compare_digest(_derive(password, record[:16]), record[16:]) and valid_format


def new_token() -> str:
    return token_urlsafe(32)


def session_digest(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def csrf_token(token: str) -> str:
    return sha256(b"hiresense-csrf:" + token.encode()).hexdigest()
