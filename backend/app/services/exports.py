from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.documents.render import ExportFormat, export_document
from app.domain.resume.models import deserialize_document
from app.repositories.errors import RevisionConflictError
from app.repositories.interfaces import ResumeRecord, VersionRecord


class ExportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    source_revision: int
    source_version_id: UUID | None
    format: ExportFormat
    size_bytes: int
    created_at: datetime


class ExportRecord(Protocol):
    id: UUID
    resume_id: UUID
    source_revision: int
    source_version_id: UUID | None
    format: str
    size_bytes: int
    created_at: datetime
    content: bytes


class ExportStore(Protocol):
    def get(self, owner_id: UUID, resume_id: UUID) -> ResumeRecord: ...
    def get_version_by_id(self, owner_id: UUID, resume_id: UUID, version_id: UUID) -> VersionRecord: ...
    def save_export(self, owner_id: UUID, resume_id: UUID, revision: int, version_id: UUID | None,
                    output: str, content: bytes) -> ExportRecord: ...
    def list_exports(self, owner_id: UUID, resume_id: UUID) -> list[ExportRecord]: ...
    def get_export(self, owner_id: UUID, resume_id: UUID, export_id: UUID) -> ExportRecord: ...


class ExportService:
    def __init__(self, scope: Callable[[UUID, bool], AbstractContextManager[ExportStore]], owner_id: UUID):
        self.scope = scope
        self.owner_id = owner_id

    def create(self, resume_id: UUID, output: ExportFormat, expected_revision: int | None,
               version_id: UUID | None) -> ExportSummary:
        with self.scope(self.owner_id, False) as store:
            if version_id is None:
                resume = store.get(self.owner_id, resume_id)
                if resume.draft_revision != expected_revision:
                    raise RevisionConflictError("Draft changed before export", resume.draft_revision)
                revision, source = resume.draft_revision, resume.draft_content
            else:
                version = store.get_version_by_id(self.owner_id, resume_id, version_id)
                revision, source = version.source_draft_revision, version.content
            document = deserialize_document(source)
        # Rendering holds no database transaction. Persist only after successful rendering.
        content = export_document(document, output)
        with self.scope(self.owner_id, True) as store:
            result = store.save_export(self.owner_id, resume_id, revision, version_id, output, content)
            return ExportSummary.model_validate(result)

    def list(self, resume_id: UUID) -> list[ExportSummary]:
        with self.scope(self.owner_id, False) as store:
            return [ExportSummary.model_validate(record) for record in store.list_exports(self.owner_id, resume_id)]

    def download(self, resume_id: UUID, export_id: UUID) -> tuple[ExportSummary, bytes]:
        with self.scope(self.owner_id, False) as store:
            record = store.get_export(self.owner_id, resume_id, export_id)
            return ExportSummary.model_validate(record), record.content
