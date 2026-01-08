from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.domain.resume.models import ResumeDocument, deserialize_document, serialize_document
from app.models import Resume, ResumeVersion
from app.repositories.errors import NotFoundError, RevisionConflictError

class ResumeMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=200)

class ResumeRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, owner_id: UUID, title: str, document: ResumeDocument,
               parent_resume_id: UUID | None = None) -> Resume:
        title = ResumeMetadata(title=title.strip()).title
        if parent_resume_id:
            self.get(owner_id, parent_resume_id)
        resume = Resume(owner_id=owner_id, title=title, draft_content=serialize_document(document),
                        parent_resume_id=parent_resume_id)
        self.session.add(resume)
        self.session.flush()
        return resume

    def get(self, owner_id: UUID, resume_id: UUID) -> Resume:
        item = self.session.scalar(select(Resume).where(Resume.id == resume_id, Resume.owner_id == owner_id)
                                   .execution_options(populate_existing=True))
        if item is None:
            raise NotFoundError("Resume not found")
        return item

    def list(self, owner_id: UUID) -> list[Resume]:
        return list(self.session.scalars(select(Resume).where(Resume.owner_id == owner_id)
                    .order_by(Resume.updated_at.desc(), Resume.id)))

    def document(self, owner_id: UUID, resume_id: UUID) -> ResumeDocument:
        return deserialize_document(self.get(owner_id, resume_id).draft_content)

    def update_draft(self, owner_id: UUID, resume_id: UUID, document: ResumeDocument,
                     expected_revision: int) -> Resume:
        if expected_revision < 1:
            raise ValueError("Expected revision must be positive")
        result = self.session.execute(update(Resume).where(
            Resume.id == resume_id, Resume.owner_id == owner_id,
            Resume.draft_revision == expected_revision,
        ).values(draft_content=serialize_document(document), draft_revision=Resume.draft_revision + 1,
                 updated_at=utc_now()).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            self.get(owner_id, resume_id)
            raise RevisionConflictError("Draft revision conflict")
        return self.get(owner_id, resume_id)

    def create_snapshot(self, owner_id: UUID, resume_id: UUID,
                        change_summary: str | None = None) -> ResumeVersion:
        if change_summary is not None and len(change_summary) > 500:
            raise ValueError("Change summary exceeds 500 characters")
        # The write locks the row before reading the draft or allocating its number.
        # All concurrent snapshot writers use this counter; unique constraint is a backstop.
        row = self.session.execute(update(Resume).where(
            Resume.id == resume_id, Resume.owner_id == owner_id,
        ).values(next_version_number=Resume.next_version_number + 1,
                 updated_at=Resume.updated_at).returning(
                     Resume.next_version_number, Resume.draft_revision, Resume.draft_content
                 ).execution_options(synchronize_session=False)).first()
        if row is None:
            raise NotFoundError("Resume not found")
        number, revision, content = row
        snapshot = ResumeVersion(resume_id=resume_id, version_number=number - 1,
                                 source_draft_revision=revision, schema_version=1,
                                 content=serialize_document(deserialize_document(content)),
                                 change_summary=change_summary)
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def get_version(self, owner_id: UUID, resume_id: UUID, version_number: int) -> ResumeVersion:
        snapshot = self.session.scalar(select(ResumeVersion).join(Resume).where(
            Resume.owner_id == owner_id, Resume.id == resume_id,
            ResumeVersion.version_number == version_number))
        if snapshot is None:
            raise NotFoundError("Version not found")
        return snapshot

    def version_document(self, owner_id: UUID, resume_id: UUID, version_number: int) -> ResumeDocument:
        return deserialize_document(self.get_version(owner_id, resume_id, version_number).content)
