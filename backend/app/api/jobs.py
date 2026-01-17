from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import Field, model_validator

from app.api.identity import resolve_owner
from app.domain.jobs.models import JobDescription
from app.schemas.resumes import RequestModel, Revision
from app.services.jobs import JobDetail, JobService, JobSummary
from app.services.resumes import Page


class JobQuery(RequestModel):
    archived: bool = False
    search: str = Field(default="", max_length=200)
    sort: Literal["updated_desc", "title_asc"] = "updated_desc"
    offset: int = Field(default=0, ge=0, le=1_000_000)
    limit: int = Field(default=20, ge=1, le=100)


class JobUpdate(RequestModel):
    expected_revision: Revision
    details: JobDescription | None = None
    archived: bool | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def replacements(self):
        if self.details is None and self.archived is None:
            raise ValueError("Provide listing details or archive status")
        return self


router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_service(request: Request, owner_id: Annotated[UUID, Depends(resolve_owner)]) -> JobService:
    return JobService(request.app.state.job_scope, owner_id)


Service = Annotated[JobService, Depends(get_service)]


@router.post("", status_code=201, response_model=JobDetail)
def create_job(job: JobDescription, service: Service, request: Request, response: Response):
    result = service.create(job)
    response.headers["Location"] = f"{request.app.state.settings.api_prefix}/jobs/{result.id}"
    return result


@router.get("", response_model=Page[JobSummary])
def list_jobs(query: Annotated[JobQuery, Query()], service: Service):
    return service.list(**query.model_dump())


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: UUID, service: Service):
    return service.get(job_id)


@router.patch("/{job_id}", response_model=JobDetail)
def change_job(job_id: UUID, body: JobUpdate, service: Service):
    return service.change(job_id, body.expected_revision, body.details, body.archived)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: UUID, expected_revision: Annotated[int, Query(ge=1)], service: Service):
    service.delete(job_id, expected_revision)
    return Response(status_code=204)
