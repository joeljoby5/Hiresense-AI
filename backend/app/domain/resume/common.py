import re
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

Text = Annotated[str, Field(max_length=10000)]
Name = Annotated[str, Field(min_length=1, max_length=200)]

class ValueModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def bounded_values(cls, value):
        if isinstance(value, (list, tuple)) and len(value) > 200:
            raise ValueError("Resume collections may contain at most 200 items")
        if isinstance(value, str) and len(value) > 10000:
            raise ValueError("Resume strings may contain at most 10000 characters")
        return value

    @field_validator("*", mode="after")
    @classmethod
    def plain_text(cls, value):
        if isinstance(value, str) and re.search(r"<\s*/?\s*[A-Za-z][^>]*>", value):
            raise ValueError("Resume text must be plain text, not HTML")
        return value

class Entry(ValueModel):
    id: UUID = Field(default_factory=uuid4)

class Bullet(Entry):
    text: Annotated[str, Field(min_length=1, max_length=2000)]

class ProfessionalLink(Entry):
    kind: str = Field(default="other", min_length=1, max_length=50)
    label: str = Field(default="", max_length=200)
    url: HttpUrl

class PartialDate(ValueModel):
    year: int = Field(ge=1, le=9999, strict=True)
    month: int | None = Field(default=None, ge=1, le=12, strict=True)

    def bounds(self) -> tuple[int, int]:
        return self.year * 12 + (self.month or 1), self.year * 12 + (self.month or 12)

def validate_range(start: PartialDate | None, end: PartialDate | None) -> None:
    if start and end and start.bounds()[0] > end.bounds()[1]:
        raise ValueError("End date precedes start date")

class DatedEntry(Entry):
    start_date: PartialDate | None = None
    end_date: PartialDate | None = None
    ongoing: bool = False

    @model_validator(mode="after")
    def dates(self):
        validate_range(self.start_date, self.end_date)
        if self.ongoing and self.end_date:
            raise ValueError("Ongoing entries cannot have an end date")
        return self
