from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from app.ai.contracts import ProviderStatus
from app.api.resumes import Service
from app.schemas.resumes import RequestModel, Revision
from app.services.writing import SummarySuggestion, WritingService


class SummaryRequest(RequestModel):
    expected_revision: Revision
    consent: bool = Field(default=False, strict=True)


router = APIRouter(prefix="/ai", tags=["Writing assistance"])


def get_writing(request: Request) -> WritingService:
    return request.app.state.writing


Writing = Annotated[WritingService, Depends(get_writing)]


@router.get("/status", response_model=ProviderStatus)
def provider_status(service: Service, writing: Writing):
    # Verify the configured owner is active even though this route has no resume.
    service.list(limit=1)
    return writing.status()


@router.post("/resumes/{resume_id}/summary", response_model=SummarySuggestion)
def suggest_summary(resume_id: UUID, body: SummaryRequest, service: Service, writing: Writing):
    return writing.suggest(service, resume_id, body.expected_revision, body.consent)
