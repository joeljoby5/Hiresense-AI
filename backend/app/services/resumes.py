from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.domain.resume.models import ResumeDocument, deserialize_document
from app.repositories.interfaces import ResumeStore, ResumeRecord, ResumeSummaryRecord, VersionRecord
from app.services.errors import IdentityUnavailableError


class ResumeSummary(BaseModel):
    id: UUID
    title: str
    draft_revision: int
    parent_resume_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ResumeDetail(ResumeSummary):
    content: ResumeDocument


class VersionSummary(BaseModel):
    id: UUID
    version_number: int
    source_draft_revision: int
    schema_version: int
    change_summary: str | None
    created_at: datetime


class VersionDetail(VersionSummary):
    content: ResumeDocument


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool


def summary(item: ResumeSummaryRecord) -> dict:
    return {name: getattr(item, name) for name in ResumeSummary.model_fields}


def detail(item: ResumeRecord) -> ResumeDetail:
    return ResumeDetail(**summary(item), content=deserialize_document(item.draft_content))


def version_detail(item: VersionRecord) -> VersionDetail:
    metadata = {name: getattr(item, name) for name in VersionSummary.model_fields}
    return VersionDetail(**metadata, content=deserialize_document(item.content))


# The supplied transaction boundary opens/closes repositories and checks an active
# owner. Services do not know about SQLAlchemy sessions, engines or HTTP requests.
TransactionScope = Callable[[UUID, bool], AbstractContextManager[ResumeStore]]


class ResumeService:
    def __init__(self, scope: TransactionScope, owner_id: UUID | None):
        if owner_id is None:
            raise IdentityUnavailableError()
        self.scope = scope
        self.owner_id = owner_id

    def create(self, title: str, content: ResumeDocument | None = None) -> ResumeDetail:
        document = content if content is not None else ResumeDocument()
        with self.scope(self.owner_id, True) as repo:
            result = detail(repo.create(self.owner_id, title, document))
        return result

    def get(self, resume_id: UUID) -> ResumeDetail:
        with self.scope(self.owner_id, False) as repo:
            return detail(repo.get(self.owner_id, resume_id))

    def list(self, limit: int = 20, offset: int = 0, search: str = "", sort: str = "updated_desc") -> Page[ResumeSummary]:
        self._pagination(limit, offset)
        if len(search) > 200 or sort not in {"updated_desc", "updated_asc", "title_asc", "title_desc"}:
            raise ValueError("Invalid list options")
        with self.scope(self.owner_id, False) as repo:
            rows, total = repo.page(self.owner_id, limit, offset, search.strip(), sort)
            return Page(items=[ResumeSummary(**summary(row)) for row in rows], total=total,
                        limit=limit, offset=offset, has_more=offset + len(rows) < total)

    def update(self, resume_id: UUID, expected_revision: int, *, title: str | None = None,
               content: ResumeDocument | None = None) -> ResumeDetail:
        self._revision(expected_revision)
        if title is None and content is None:
            raise ValueError("At least one mutable field is required")
        with self.scope(self.owner_id, True) as repo:
            result = detail(repo.update_state(self.owner_id, resume_id, expected_revision,
                                              title=title, document=content))
        return result

    def delete(self, resume_id: UUID, expected_revision: int) -> None:
        self._revision(expected_revision)
        with self.scope(self.owner_id, True) as repo:
            repo.delete(self.owner_id, resume_id, expected_revision)

    def duplicate(self, resume_id: UUID, title: str | None = None) -> ResumeDetail:
        with self.scope(self.owner_id, True) as repo:
            source = repo.get(self.owner_id, resume_id)
            copy_title = title if title is not None else source.title[:193].rstrip() + " (copy)"
            # Entry IDs are scoped to a document and deliberately preserved.
            content = deserialize_document(source.draft_content)
            result = detail(repo.create(self.owner_id, copy_title, content, parent_resume_id=source.id))
        return result

    def checkpoint(self, resume_id: UUID, expected_revision: int, change_summary: str | None = None) -> VersionDetail:
        self._revision(expected_revision)
        with self.scope(self.owner_id, True) as repo:
            result = version_detail(repo.create_snapshot(self.owner_id, resume_id, change_summary,
                                                        expected_revision=expected_revision))
        return result

    def versions(self, resume_id: UUID, limit: int = 20, offset: int = 0) -> Page[VersionSummary]:
        self._pagination(limit, offset)
        with self.scope(self.owner_id, False) as repo:
            rows, total = repo.version_page(self.owner_id, resume_id, limit, offset)
            items = [VersionSummary(**{name: getattr(row, name) for name in VersionSummary.model_fields}) for row in rows]
            return Page(items=items, total=total, limit=limit, offset=offset, has_more=offset + len(rows) < total)

    def version(self, resume_id: UUID, version_id: UUID) -> VersionDetail:
        with self.scope(self.owner_id, False) as repo:
            return version_detail(repo.get_version_by_id(self.owner_id, resume_id, version_id))

    @staticmethod
    def _revision(expected_revision: int) -> None:
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("Expected revision must be a positive integer")

    @staticmethod
    def _pagination(limit: int, offset: int) -> None:
        if not 1 <= limit <= 100 or not 0 <= offset <= 1_000_000:
            raise ValueError("Invalid pagination")
