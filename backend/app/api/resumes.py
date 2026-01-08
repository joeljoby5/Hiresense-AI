from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.identity import resolve_owner
from app.schemas.errors import APIErrorResponse
from app.schemas.resumes import (
    ResumeCreateRequest, ResumeUpdateRequest, ResumeDuplicateRequest, ResumeVersionCreateRequest,
    ResumeListQuery, VersionListQuery, ResumeDetailResponse, ResumeListResponse,
    ResumeVersionDetailResponse, ResumeVersionListResponse,
)
from app.services.resumes import ResumeService

ERRORS = {status: {"model": APIErrorResponse} for status in (404, 409, 413, 422, 500, 503)}
router = APIRouter(prefix="/resumes", responses=ERRORS)


def get_service(request: Request, owner_id: Annotated[UUID, Depends(resolve_owner)]) -> ResumeService:
    return ResumeService(request.app.state.resume_scope, owner_id)


Service = Annotated[ResumeService, Depends(get_service)]


@router.post("", status_code=201, response_model=ResumeDetailResponse, tags=["Resumes"], summary="Create a resume",
             description="Requires initialized, explicitly enabled local development identity. Omitted content creates an empty draft.")
def create_resume(body: ResumeCreateRequest, service: Service, response: Response, request: Request):
    result = service.create(body.title, body.content)
    response.headers["Location"] = f"{request.app.state.settings.api_prefix}/resumes/{result.id}"
    return result


@router.get("", response_model=ResumeListResponse, tags=["Resumes"], summary="List owned resumes",
            description="Bounded metadata only. Search is literal title substring matching; SQLite folds ASCII case only. Sort ties use UUID ascending.")
def list_resumes(service: Service, query: Annotated[ResumeListQuery, Query()]):
    return service.list(**query.model_dump())


@router.get("/{resume_id}", response_model=ResumeDetailResponse, tags=["Resumes"], summary="Retrieve a resume")
def get_resume(resume_id: UUID, service: Service):
    return service.get(resume_id)


@router.patch("/{resume_id}", response_model=ResumeDetailResponse, tags=["Resumes"], summary="Replace title or working draft",
              description="Title and content share one revision. Supply expected_revision. Null replacements are rejected; content is replaced completely.")
def update_resume(resume_id: UUID, body: ResumeUpdateRequest, service: Service):
    return service.update(resume_id, **body.model_dump(exclude_unset=True, exclude={"content"}),
                          content=body.content)


@router.delete("/{resume_id}", status_code=204, tags=["Resumes"], summary="Delete a resume and its checkpoints",
               description="Requires expected_revision. Independent children survive with lineage cleared and revisions incremented.")
def delete_resume(resume_id: UUID, service: Service, expected_revision: Annotated[int, Query(ge=1)]):
    service.delete(resume_id, expected_revision)
    return Response(status_code=204)


@router.post("/{resume_id}/duplicate", status_code=201, response_model=ResumeDetailResponse,
             tags=["Resumes"], summary="Create an independent copy")
def duplicate_resume(resume_id: UUID, service: Service, response: Response, request: Request,
                     body: ResumeDuplicateRequest | None = None):
    result = service.duplicate(resume_id, body.title if body else None)
    response.headers["Location"] = f"{request.app.state.settings.api_prefix}/resumes/{result.id}"
    return result


@router.post("/{resume_id}/versions", status_code=201, response_model=ResumeVersionDetailResponse,
             tags=["Resume versions"], summary="Checkpoint an exact draft revision")
def create_version(resume_id: UUID, body: ResumeVersionCreateRequest, service: Service,
                   response: Response, request: Request):
    result = service.checkpoint(resume_id, body.expected_revision, body.change_summary)
    response.headers["Location"] = f"{request.app.state.settings.api_prefix}/resumes/{resume_id}/versions/{result.id}"
    return result


@router.get("/{resume_id}/versions", response_model=ResumeVersionListResponse,
            tags=["Resume versions"], summary="List checkpoint metadata")
def list_versions(resume_id: UUID, service: Service, query: Annotated[VersionListQuery, Query()]):
    return service.versions(resume_id, **query.model_dump())


@router.get("/{resume_id}/versions/{version_id}", response_model=ResumeVersionDetailResponse,
            tags=["Resume versions"], summary="Retrieve an immutable checkpoint")
def get_version(resume_id: UUID, version_id: UUID, service: Service):
    return service.version(resume_id, version_id)
