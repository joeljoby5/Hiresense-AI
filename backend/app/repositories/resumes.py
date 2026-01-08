from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete, func
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
        return self.update_state(owner_id, resume_id, expected_revision, document=document)

    def update_state(self, owner_id: UUID, resume_id: UUID, expected_revision: int,
                     *, title: str | None = None, document: ResumeDocument | None = None) -> Resume:
        if expected_revision < 1:
            raise ValueError("Expected revision must be positive")
        values = {"draft_revision": Resume.draft_revision + 1, "updated_at": utc_now()}
        if title is not None:
            values["title"] = ResumeMetadata(title=title.strip()).title
        if document is not None:
            values["draft_content"] = serialize_document(document)
        result = self.session.execute(update(Resume).where(
            Resume.id == resume_id, Resume.owner_id == owner_id,
            Resume.draft_revision == expected_revision,
        ).values(**values).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            current = self.get(owner_id, resume_id)
            raise RevisionConflictError("Draft revision conflict", current.draft_revision)
        return self.get(owner_id, resume_id)

    def create_snapshot(self, owner_id: UUID, resume_id: UUID,
                        change_summary: str | None = None,
                        expected_revision: int | None = None) -> ResumeVersion:
        if change_summary is not None and len(change_summary) > 500:
            raise ValueError("Change summary exceeds 500 characters")
        # The write locks the row before reading the draft or allocating its number.
        # All concurrent snapshot writers use this counter; unique constraint is a backstop.
        conditions = [Resume.id == resume_id, Resume.owner_id == owner_id]
        if expected_revision is not None:
            if expected_revision < 1:
                raise ValueError("Expected revision must be positive")
            conditions.append(Resume.draft_revision == expected_revision)
        row = self.session.execute(update(Resume).where(*conditions).values(next_version_number=Resume.next_version_number + 1,
                 updated_at=Resume.updated_at).returning(
                     Resume.next_version_number, Resume.draft_revision, Resume.draft_content
                 ).execution_options(synchronize_session=False)).first()
        if row is None:
            current = self.get(owner_id, resume_id)
            raise RevisionConflictError("Draft revision conflict", current.draft_revision)
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

    def page(self, owner_id: UUID, limit: int, offset: int, search: str, sort: str):
        conditions = [Resume.owner_id == owner_id]
        if search:
            # contains(autoescape) treats %, _ and / literally, with bound parameters.
            conditions.append(Resume.title.icontains(search, autoescape=True))
        count = self.session.scalar(select(func.count()).select_from(Resume).where(*conditions))
        ordering = {
            "updated_desc": Resume.updated_at.desc(), "updated_asc": Resume.updated_at.asc(),
            "title_asc": Resume.title.asc(), "title_desc": Resume.title.desc(),
        }[sort]
        # Metadata only: do not load canonical documents for library listings.
        columns = (Resume.id, Resume.title, Resume.draft_revision, Resume.parent_resume_id,
                   Resume.created_at, Resume.updated_at)
        rows = self.session.execute(select(*columns).where(*conditions)
            .order_by(ordering, Resume.id).limit(limit).offset(offset)).all()
        return rows, count

    def delete(self, owner_id: UUID, resume_id: UUID, expected_revision: int) -> None:
        # Lock/check the parent before detaching children. Children remain independent.
        result = self.session.execute(update(Resume).where(
            Resume.id == resume_id, Resume.owner_id == owner_id,
            Resume.draft_revision == expected_revision,
        ).values(updated_at=Resume.updated_at).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            current = self.get(owner_id, resume_id)
            raise RevisionConflictError("Draft revision conflict", current.draft_revision)
        self.session.execute(update(Resume).where(
            Resume.parent_resume_id == resume_id, Resume.owner_id == owner_id,
        ).values(parent_resume_id=None, draft_revision=Resume.draft_revision + 1,
                 updated_at=utc_now()).execution_options(synchronize_session=False))
        self.session.execute(delete(Resume).where(Resume.id == resume_id, Resume.owner_id == owner_id))

    def version_page(self, owner_id: UUID, resume_id: UUID, limit: int, offset: int):
        self.get(owner_id, resume_id)
        count = self.session.scalar(select(func.count()).select_from(ResumeVersion)
                                   .where(ResumeVersion.resume_id == resume_id))
        columns = (ResumeVersion.id, ResumeVersion.version_number, ResumeVersion.source_draft_revision,
                   ResumeVersion.schema_version, ResumeVersion.change_summary, ResumeVersion.created_at)
        rows = self.session.execute(select(*columns).where(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc(), ResumeVersion.id).limit(limit).offset(offset)).all()
        return rows, count

    def get_version_by_id(self, owner_id: UUID, resume_id: UUID, version_id: UUID) -> ResumeVersion:
        self.get(owner_id, resume_id)
        snapshot = self.session.scalar(select(ResumeVersion).where(
            ResumeVersion.resume_id == resume_id, ResumeVersion.id == version_id))
        if snapshot is None:
            raise NotFoundError("Version not found")
        return snapshot
