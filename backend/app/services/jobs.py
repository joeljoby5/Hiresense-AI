from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.jobs.models import JobDescription
from app.domain.intelligence.requirements import extract_requirements
from app.services.resumes import Page


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    company: str
    archived: bool
    revision: int
    created_at: datetime
    updated_at: datetime


class JobDetail(JobSummary):
    details: JobDescription


class JobRecord(Protocol):
    id: UUID
    title: str
    company: str
    content: dict
    archived: bool
    revision: int
    created_at: datetime
    updated_at: datetime


class JobStore(Protocol):
    def add(self, owner_id: UUID, job: JobDescription) -> JobRecord: ...
    def get(self, owner_id: UUID, job_id: UUID) -> JobRecord: ...
    def page(self, owner_id: UUID, archived: bool, search: str, sort: str,
             offset: int, limit: int) -> tuple[Sequence[JobRecord], int]: ...
    def change(self, owner_id: UUID, job_id: UUID, revision: int, job: JobDescription | None,
               archived: bool | None) -> JobRecord: ...
    def remove(self, owner_id: UUID, job_id: UUID, revision: int) -> None: ...


def detail(record: JobRecord) -> JobDetail:
    metadata = JobSummary.model_validate(record)
    content = JobDescription(title=metadata.title, company=metadata.company, **record.content)
    return JobDetail(**metadata.model_dump(), details=content)


class JobService:
    def __init__(self, scope: Callable[[UUID, bool], AbstractContextManager[JobStore]], owner_id: UUID):
        self.scope = scope
        self.owner_id = owner_id

    def create(self, job: JobDescription) -> JobDetail:
        with self.scope(self.owner_id, True) as store:
            return detail(store.add(self.owner_id, job))

    def get(self, job_id: UUID) -> JobDetail:
        with self.scope(self.owner_id, False) as store:
            return detail(store.get(self.owner_id, job_id))

    def requirements(self, job_id: UUID):
        job = self.get(job_id)
        return extract_requirements(job.details.description, job.title)

    def list(self, archived: bool, search: str, sort: str, offset: int, limit: int) -> Page[JobSummary]:
        with self.scope(self.owner_id, False) as store:
            rows, total = store.page(self.owner_id, archived, search.strip(), sort, offset, limit)
            return Page(items=[JobSummary.model_validate(row) for row in rows], total=total,
                        offset=offset, limit=limit, has_more=offset + len(rows) < total)

    def change(self, job_id: UUID, expected_revision: int, details: JobDescription | None, archived: bool | None) -> JobDetail:
        with self.scope(self.owner_id, True) as store:
            return detail(store.change(self.owner_id, job_id, expected_revision, details, archived))

    def delete(self, job_id: UUID, expected_revision: int) -> None:
        with self.scope(self.owner_id, True) as store:
            store.remove(self.owner_id, job_id, expected_revision)
