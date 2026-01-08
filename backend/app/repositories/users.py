from uuid import UUID
from pydantic import TypeAdapter, EmailStr
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.models import User

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_development_owner(self, email: str, settings: Settings) -> User:
        if settings.environment != "development":
            raise ValueError("Development identities require the development environment")
        # Deliberate case-insensitive identity policy, including local part.
        normalized = str(TypeAdapter(EmailStr).validate_python(email.strip())).casefold()
        owner = User(email=normalized, password_hash=None)
        self.session.add(owner)
        self.session.flush()
        return owner

    def get(self, owner_id: UUID) -> User | None:
        return self.session.get(User, owner_id)
