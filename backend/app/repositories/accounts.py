from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.account_session import AccountSession
from app.models.resume import Resume
from app.models.user import User


class AccountRepository:
    def __init__(self, session: Session):
        self.session = session

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def create(self, email: str, password: str, name: str) -> User:
        owner = User(email=email, password_hash=password, display_name=name)
        self.session.add(owner)
        self.session.flush()
        return owner

    def resolve(self, digest: str) -> User | None:
        return self.session.scalar(select(User).join(AccountSession, AccountSession.owner_id == User.id).where(
            AccountSession.token_digest == digest, AccountSession.expires_at > utc_now(), User.is_active.is_(True),
        ))

    def issue(self, owner_id: UUID, digest: str, expiry: datetime) -> None:
        self.session.execute(delete(AccountSession).where(AccountSession.expires_at <= utc_now()))
        self.session.add(AccountSession(token_digest=digest, owner_id=owner_id, expires_at=expiry))
        self.session.flush()
        older = (select(AccountSession.token_digest).where(AccountSession.owner_id == owner_id)
                 .order_by(AccountSession.created_at.desc(), AccountSession.token_digest).offset(10))
        self.session.execute(delete(AccountSession).where(AccountSession.token_digest.in_(older)))

    def revoke(self, digest: str) -> None:
        self.session.execute(delete(AccountSession).where(AccountSession.token_digest == digest))

    def revoke_all(self, owner_id: UUID) -> None:
        self.session.execute(delete(AccountSession).where(AccountSession.owner_id == owner_id))

    def remove(self, owner_id: UUID) -> None:
        self.session.execute(update(Resume).where(Resume.owner_id == owner_id).values(parent_resume_id=None))
        self.session.execute(delete(Resume).where(Resume.owner_id == owner_id))
        self.session.execute(delete(User).where(User.id == owner_id))
