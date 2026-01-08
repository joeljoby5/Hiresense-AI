from pydantic import BaseModel, Field


class FieldError(BaseModel):
    field: list[str | int]
    code: str


class APIError(BaseModel):
    code: str
    message: str
    request_id: str
    current_revision: int | None = None
    fields: list[FieldError] = Field(default_factory=list)


class APIErrorResponse(BaseModel):
    error: APIError
