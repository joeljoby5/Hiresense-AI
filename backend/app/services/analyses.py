from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import asdict
from datetime import datetime
import json
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.intelligence.ats import Analysis, run_analysis
from app.domain.intelligence.requirements import extract_requirements
from app.domain.resume.models import deserialize_document
from app.repositories.errors import JobConflict, RevisionConflictError
from app.repositories.interfaces import ResumeRecord, VersionRecord
from app.services.jobs import JobRecord


class AnalysisLimitError(Exception):
    pass


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    resume_revision: int
    resume_version_id: UUID | None
    job_id: UUID
    job_revision: int
    created_at: datetime


class AnalysisDetail(AnalysisSummary):
    report: Analysis


class AnalysisRecord(Protocol):
    id: UUID
    resume_id: UUID
    resume_revision: int
    resume_version_id: UUID | None
    job_id: UUID
    job_revision: int
    created_at: datetime
    report: dict


class AnalysisStore(Protocol):
    def get(self, owner_id: UUID, resume_id: UUID) -> ResumeRecord: ...
    def get_version_by_id(self, owner_id: UUID, resume_id: UUID, version_id: UUID) -> VersionRecord: ...
    def job(self, owner_id: UUID, job_id: UUID) -> JobRecord: ...
    def save_analysis(self, owner_id: UUID, resume_id: UUID, job_id: UUID, **payload) -> AnalysisRecord: ...
    def analyses(self, owner_id: UUID) -> Sequence[AnalysisRecord]: ...
    def analysis(self, owner_id: UUID, analysis_id: UUID) -> AnalysisRecord: ...


class AnalysisService:
    def __init__(self, scope: Callable[[UUID, bool], AbstractContextManager[AnalysisStore]], owner_id: UUID):
        self.scope = scope
        self.owner_id = owner_id

    def run(self, resume_id: UUID, job_id: UUID, job_revision: int,
            resume_revision: int | None, resume_version_id: UUID | None) -> AnalysisDetail:
        with self.scope(self.owner_id, False) as store:
            listing = store.job(self.owner_id, job_id)
            if listing.revision != job_revision:
                raise JobConflict("Job changed before analysis", listing.revision)
            description = listing.content["description"]
            title = listing.title
            if resume_version_id:
                version = store.get_version_by_id(self.owner_id, resume_id, resume_version_id)
                revision, draft = version.source_draft_revision, version.content
            else:
                resume = store.get(self.owner_id, resume_id)
                if resume.draft_revision != resume_revision:
                    raise RevisionConflictError("Resume changed before analysis", resume.draft_revision)
                revision, draft = resume.draft_revision, resume.draft_content
            document = deserialize_document(draft)
        # Retain the scoring inputs while removing direct personal fields used only for presence checks.
        extraction = extract_requirements(description, title)
        analysis = run_analysis(document, extraction)
        source = {"resume": document.model_dump(mode="json"), "job_requirements": asdict(extraction)}
        contact = source["resume"].pop("personal_information")
        source["contact_presence"] = {"email": bool(contact["email"]), "phone": bool(contact["phone"])}
        report = asdict(analysis)
        if len(json.dumps((source, report), ensure_ascii=False).encode("utf-8")) > 2 * 1024 * 1024:
            raise AnalysisLimitError()
        with self.scope(self.owner_id, True) as store:
            row = store.save_analysis(self.owner_id, resume_id, job_id, resume_revision=revision,
                                      resume_version_id=resume_version_id, job_revision=job_revision,
                                      source=source, report=report)
            return AnalysisDetail.model_validate(row)

    def get(self, analysis_id: UUID) -> AnalysisDetail:
        with self.scope(self.owner_id, False) as store:
            return AnalysisDetail.model_validate(store.analysis(self.owner_id, analysis_id))

    def list(self) -> list[AnalysisSummary]:
        with self.scope(self.owner_id, False) as store:
            return [AnalysisSummary.model_validate(row) for row in store.analyses(self.owner_id)]
