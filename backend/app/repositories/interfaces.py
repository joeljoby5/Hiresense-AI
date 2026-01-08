"""Structural boundary for the existing resume repository; no ORM dependencies."""
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.resume.models import ResumeDocument


class ResumeSummaryRecord(Protocol):
    id: UUID
    title: str
    draft_revision: int
    parent_resume_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ResumeRecord(ResumeSummaryRecord, Protocol):
    draft_content: dict


class VersionSummaryRecord(Protocol):
    id: UUID
    version_number: int
    source_draft_revision: int
    schema_version: int
    change_summary: str | None
    created_at: datetime


class VersionRecord(VersionSummaryRecord, Protocol):
    content: dict


class ResumeStore(Protocol):
    def create(self, owner_id: UUID, title: str, document: ResumeDocument,
               parent_resume_id: UUID | None = None) -> ResumeRecord: ...

    def get(self, owner_id: UUID, resume_id: UUID) -> ResumeRecord: ...

    def page(self, owner_id: UUID, limit: int, offset: int, search: str,
             sort: str) -> tuple[Sequence[ResumeSummaryRecord], int]: ...

    def update_state(self, owner_id: UUID, resume_id: UUID, expected_revision: int, *,
                     title: str | None = None, document: ResumeDocument | None = None) -> ResumeRecord: ...

    def delete(self, owner_id: UUID, resume_id: UUID, expected_revision: int) -> None: ...

    def create_snapshot(self, owner_id: UUID, resume_id: UUID, change_summary: str | None = None,
                        expected_revision: int | None = None) -> VersionRecord: ...

    def version_page(self, owner_id: UUID, resume_id: UUID, limit: int,
                     offset: int) -> tuple[Sequence[VersionSummaryRecord], int]: ...

    def get_version_by_id(self, owner_id: UUID, resume_id: UUID, version_id: UUID) -> VersionRecord: ...
