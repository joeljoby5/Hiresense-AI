from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class JobDescription(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Name
    company: Name
    description: str = Field(min_length=1, max_length=40_000)
    listing_url: HttpUrl | None = None
    location: str = Field(default="", max_length=200)
    employment_type: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=5_000)
