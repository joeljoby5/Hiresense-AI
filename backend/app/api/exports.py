from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import model_validator

from app.api.identity import resolve_owner
from app.documents.render import ExportFormat, MEDIA_TYPES
from app.schemas.resumes import RequestModel, Revision
from app.services.exports import ExportService, ExportSummary


class ExportRequest(RequestModel):
    format: ExportFormat
    expected_revision: Revision | None = None
    version_id: UUID | None = None

    @model_validator(mode="after")
    def one_source(self):
        if (self.expected_revision is None) == (self.version_id is None):
            raise ValueError("Choose one source revision or version")
        return self


router = APIRouter(prefix="/resumes/{resume_id}/exports", tags=["Resume exports"])


def get_service(request: Request, owner_id: Annotated[UUID, Depends(resolve_owner)]) -> ExportService:
    return ExportService(request.app.state.export_scope, owner_id)


Service = Annotated[ExportService, Depends(get_service)]


@router.post("", status_code=201, response_model=ExportSummary)
def create_export(resume_id: UUID, body: ExportRequest, service: Service, response: Response, request: Request):
    result = service.create(resume_id, body.format, body.expected_revision, body.version_id)
    response.headers["Location"] = f"{request.app.state.settings.api_prefix}/resumes/{resume_id}/exports/{result.id}"
    return result


@router.get("", response_model=list[ExportSummary])
def list_exports(resume_id: UUID, service: Service):
    return service.list(resume_id)


@router.get("/{export_id}", response_class=Response)
def download_export(resume_id: UUID, export_id: UUID, service: Service):
    metadata, content = service.download(resume_id, export_id)
    filename = f"resume-r{metadata.source_revision}.{metadata.format}"
    return Response(content, media_type=MEDIA_TYPES[metadata.format], headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })
