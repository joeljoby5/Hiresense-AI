from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.security.credentials import csrf_token, new_token, password_hash, password_valid, session_digest
from app.services.errors import AccountExists, AuthenticationRequired, InvalidCredentials

SESSION_SECONDS = 12 * 60 * 60


class Profile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str


class AccountState(BaseModel):
    profile: Profile
    csrf_token: str


@dataclass(frozen=True)
class SignIn:
    token: str
    state: AccountState


class UserRecord(Protocol):
    id: UUID
    email: str
    password_hash: str | None
    display_name: str
    is_active: bool


class AccountStore(Protocol):
    def by_email(self, email: str) -> UserRecord | None: ...
    def create(self, email: str, password: str, name: str) -> UserRecord: ...
    def resolve(self, digest: str) -> UserRecord | None: ...
    def issue(self, owner_id: UUID, digest: str, expiry: datetime) -> None: ...
    def revoke(self, digest: str) -> None: ...
    def revoke_all(self, owner_id: UUID) -> None: ...
    def remove(self, owner_id: UUID) -> None: ...


class AccountService:
    def __init__(self, scope: Callable[[bool], AbstractContextManager[AccountStore]]):
        self.scope = scope

    @staticmethod
    def _active(store: AccountStore, token: str) -> UserRecord:
        owner = store.resolve(session_digest(token))
        if owner is None:
            raise AuthenticationRequired()
        return owner

    @staticmethod
    def _state(owner: UserRecord, token: str) -> AccountState:
        return AccountState(profile=Profile.model_validate(owner), csrf_token=csrf_token(token))

    def _issue(self, store: AccountStore, owner: UserRecord, previous: str | None = None) -> SignIn:
        if previous:
            store.revoke(session_digest(previous))
        token = new_token()
        store.issue(owner.id, session_digest(token), datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS))
        return SignIn(token, self._state(owner, token))

    def register(self, email: str, password: str, name: str, previous: str | None = None) -> SignIn:
        hashed = password_hash(password)
        with self.scope(True) as store:
            if store.by_email(email) is not None:
                raise AccountExists()
            return self._issue(store, store.create(email, hashed, name), previous)

    def login(self, email: str, password: str, previous: str | None = None) -> SignIn:
        with self.scope(False) as store:
            owner = store.by_email(email)
            hashed = owner.password_hash if owner and owner.is_active else None
        if not password_valid(password, hashed):
            raise InvalidCredentials()
        with self.scope(True) as store:
            owner = store.by_email(email)
            if not owner or not owner.is_active or owner.password_hash != hashed:
                raise InvalidCredentials()
            return self._issue(store, owner, previous)

    def current(self, token: str) -> AccountState:
        with self.scope(False) as store:
            return self._state(self._active(store, token), token)

    def logout(self, token: str):
        with self.scope(True) as store:
            store.revoke(session_digest(token))

    def profile(self, token: str, name: str) -> AccountState:
        with self.scope(True) as store:
            owner = self._active(store, token)
            owner.display_name = name
            return self._state(owner, token)

    def revoke_all(self, token: str) -> SignIn:
        with self.scope(True) as store:
            owner = self._active(store, token)
            store.revoke_all(owner.id)
            return self._issue(store, owner)

    def _verified_hash(self, token: str, password: str) -> str:
        with self.scope(False) as store:
            hashed = self._active(store, token).password_hash
        if not password_valid(password, hashed):
            raise InvalidCredentials()
        return hashed

    def update_password(self, token: str, old: str, new: str) -> SignIn:
        verified = self._verified_hash(token, old)
        hashed = password_hash(new)
        with self.scope(True) as store:
            owner = self._active(store, token)
            if owner.password_hash != verified:
                raise InvalidCredentials()
            owner.password_hash = hashed
            store.revoke_all(owner.id)
            return self._issue(store, owner)

    def delete(self, token: str, password: str) -> None:
        verified = self._verified_hash(token, password)
        with self.scope(True) as store:
            owner = self._active(store, token)
            if owner.password_hash != verified:
                raise InvalidCredentials()
            store.remove(owner.id)
