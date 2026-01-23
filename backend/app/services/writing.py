from threading import BoundedSemaphore
from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.ai.contracts import InvalidProviderResponse, ProviderRateLimited, ProviderStatus, ProviderUnavailable, WritingProvider
from app.domain.resume.models import ResumeDocument
from app.repositories.errors import RevisionConflictError
from app.services.resumes import ResumeService


class SuggestionInputError(Exception):
    pass


class SummarySuggestion(BaseModel):
    source_revision: int
    original: str
    proposed: str
    explanation: str
    provider: str
    model: str | None
    mock: bool


class WritingService:
    def __init__(self, provider: WritingProvider):
        self.provider = provider
        self.slots = BoundedSemaphore(1)

    def status(self) -> ProviderStatus:
        if not self.slots.acquire(blocking=False):
            raise ProviderRateLimited()
        try:
            return self.provider.status()
        finally:
            self.slots.release()

    def suggest(self, service: ResumeService, resume_id: UUID, revision: int, consent: bool) -> SummarySuggestion:
        resume = service.get(resume_id)
        if resume.draft_revision != revision:
            raise RevisionConflictError("Resume changed before suggestion", resume.draft_revision)
        original = resume.content.professional_summary
        if not original:
            raise SuggestionInputError()
        if not self.slots.acquire(blocking=False):
            raise ProviderRateLimited()
        try:
            status = self.provider.status()
            if not status.available:
                raise ProviderUnavailable()
            if not status.mock and not consent:
                raise SuggestionInputError()
            proposal = self.provider.rewrite_summary(original)
            try:
                ResumeDocument(professional_summary=proposal.proposed)
            except ValidationError as exc:
                raise InvalidProviderResponse() from exc
            return SummarySuggestion(source_revision=revision, original=original, proposed=proposal.proposed,
                                     explanation=proposal.explanation, provider=status.provider, model=status.model,
                                     mock=status.mock)
        finally:
            self.slots.release()
