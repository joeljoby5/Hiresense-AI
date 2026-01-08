"""Explicit, idempotent local bootstrap: python -m app.initialize_owner."""
from sqlalchemy import select

from app.core.config import Settings
from app.database.session import build_engine, session_factory, transaction
from app.models import User
from app.repositories.users import UserRepository

DEVELOPMENT_EMAIL = "local-developer@example.org"


def initialize_owner(settings: Settings):
    if settings.environment != "development" or not settings.development_identity_enabled:
        raise ValueError("Explicit development identity mode is required")
    engine = build_engine(settings)
    try:
        with transaction(session_factory(engine)) as session:
            session.connection(execution_options={"sqlite_write": True})
            owner = session.scalar(select(User).where(User.email == DEVELOPMENT_EMAIL))
            if owner is None:
                owner = UserRepository(session).create_development_owner(DEVELOPMENT_EMAIL, settings)
            if not owner.is_active:
                raise ValueError("The development owner is inactive")
            if settings.development_owner_id is not None and settings.development_owner_id != owner.id:
                raise ValueError("Configured owner differs from the bootstrap owner")
            return owner.id
    finally:
        engine.dispose()


def main():
    try:
        owner_id = initialize_owner(Settings())
    except Exception:
        # Database errors may contain private paths/parameters; never print them.
        raise SystemExit("Owner initialization failed. Check development mode and migrated database.") from None
    print(f"HIRESENSE_DEVELOPMENT_OWNER_ID={owner_id}")


if __name__ == "__main__":
    main()
