from contextlib import contextmanager
from uuid import UUID

from app.database.session import transaction
from app.repositories.resumes import ResumeRepository
from app.repositories.users import UserRepository
from app.services.errors import IdentityUnavailableError


def resume_scope(factory):
    @contextmanager
    def scope(owner_id: UUID, write: bool):
        with transaction(factory) as session:
            # Acquire SQLite's writer reservation before identity/source reads.
            # This avoids read-to-write upgrade failures in multi-step workflows.
            session.connection(execution_options={"sqlite_write": write})
            owner = UserRepository(session).get(owner_id)
            if owner is None or not owner.is_active:
                raise IdentityUnavailableError()
            yield ResumeRepository(session)
    return scope
