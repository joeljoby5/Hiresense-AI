from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.resume.models import ResumeDocument
from app.services.resumes import ResumeDetail, ResumeSummary, VersionDetail, VersionSummary, Page

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Revision = Annotated[int, Field(strict=True, ge=1)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResumeCreateRequest(RequestModel):
    title: Title
    content: ResumeDocument = Field(default_factory=ResumeDocument)


class ResumeUpdateRequest(RequestModel):
    expected_revision: Revision
    title: Title | None = None
    content: ResumeDocument | None = None

    @model_validator(mode="after")
    def replacements(self):
        supplied = self.model_fields_set & {"title", "content"}
        if not supplied or any(getattr(self, name) is None for name in supplied):
            raise ValueError("Supply title or content; explicit null replacements are not allowed")
        return self


class ResumeDuplicateRequest(RequestModel):
    title: Title | None = None

    @model_validator(mode="after")
    def title_not_null(self):
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Omit title to use the copy title; null is not allowed")
        return self


class ResumeVersionCreateRequest(RequestModel):
    expected_revision: Revision
    change_summary: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class ResumeListQuery(RequestModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)
    search: str = Field(default="", max_length=200)
    sort: Literal["updated_desc", "updated_asc", "title_asc", "title_desc"] = "updated_desc"


class VersionListQuery(RequestModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)


ResumeDetailResponse = ResumeDetail
ResumeListResponse = Page[ResumeSummary]
ResumeVersionDetailResponse = VersionDetail
ResumeVersionListResponse = Page[VersionSummary]
