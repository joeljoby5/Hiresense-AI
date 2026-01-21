from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import model_validator

from app.api.identity import resolve_owner
from app.schemas.resumes import RequestModel, Revision
from app.services.analyses import AnalysisDetail, AnalysisService, AnalysisSummary


class AnalysisRequest(RequestModel):
    resume_id: UUID
    resume_revision: Revision | None = None
    resume_version_id: UUID | None = None
    job_id: UUID
    job_revision: Revision

    @model_validator(mode="after")
    def one_source(self):
        if (self.resume_revision is None) == (self.resume_version_id is None):
            raise ValueError("Choose one resume draft or checkpoint")
        return self


router = APIRouter(prefix="/analyses", tags=["ATS analysis"])


def get_service(request: Request, owner_id: Annotated[UUID, Depends(resolve_owner)]) -> AnalysisService:
    return AnalysisService(request.app.state.analysis_scope, owner_id)


Service = Annotated[AnalysisService, Depends(get_service)]


@router.post("", status_code=201, response_model=AnalysisDetail)
def analyze(body: AnalysisRequest, service: Service, request: Request, response: Response):
    outcome = service.run(**body.model_dump())
    response.headers["Location"] = f"{request.app.state.settings.api_prefix}/analyses/{outcome.id}"
    return outcome


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(service: Service):
    return service.list()


@router.get("/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: UUID, service: Service):
    return service.get(analysis_id)
