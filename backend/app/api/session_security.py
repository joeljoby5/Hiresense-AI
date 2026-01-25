from ipaddress import ip_address
import re
from hmac import compare_digest
from urllib.parse import urlsplit

from fastapi import Request

from app.security.credentials import csrf_token
from app.services.errors import AuthenticationRequired, CsrfRejected

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
_CSRF_PATTERN = re.compile(r"[0-9a-f]{64}")


def is_loopback(request: Request) -> bool:
    try:
        return request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        return False


def secure_cookie(request: Request) -> bool:
    return not (request.app.state.settings.environment == "development" and is_loopback(request))


def cookie_name(request: Request) -> str:
    return "__Host-hiresense_session" if secure_cookie(request) else "hiresense_session"


def session_token(request: Request) -> str | None:
    value = request.cookies.get(cookie_name(request))
    if value is not None and not _TOKEN_PATTERN.fullmatch(value):
        raise AuthenticationRequired()
    return value


def require_origin(request: Request) -> None:
    origins = request.headers.getlist("origin")
    if len(origins) != 1 or origins[0] not in request.app.state.settings.allowed_origins:
        raise CsrfRejected()
    origin = urlsplit(origins[0])
    if origin.scheme == "https":
        return
    try:
        local_origin = origin.hostname == "localhost" or ip_address(origin.hostname).is_loopback
    except ValueError:
        local_origin = False
    if secure_cookie(request) or not local_origin:
        raise CsrfRejected()


def require_csrf(request: Request, token: str) -> None:
    require_origin(request)
    value = request.headers.get("x-csrf-token", "")
    if not _CSRF_PATTERN.fullmatch(value) or not compare_digest(value, csrf_token(token)):
        raise CsrfRejected()
