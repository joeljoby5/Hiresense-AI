from uuid import UUID
from pydantic import EmailStr, Field, HttpUrl, model_validator

from app.domain.resume.common import (
    Bullet, DatedEntry, Entry, Name, PartialDate, ProfessionalLink, Text, ValueModel, validate_range,
)

class PersonalInformation(ValueModel):
    full_name: str = Field(default="", max_length=200)
    headline: str = Field(default="", max_length=300)
    email: EmailStr | None = None
    phone: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=300)
    links: list[ProfessionalLink] = Field(default_factory=list)

class Experience(DatedEntry):
    organization: str = Field(default="", max_length=200)
    position: str = Field(default="", max_length=200)
    employment_type: str | None = Field(default=None, max_length=100)
    location: str = Field(default="", max_length=300)
    description: Text = ""
    bullets: list[Bullet] = Field(default_factory=list)
    technologies: list[Name] = Field(default_factory=list)

class AcademicScore(ValueModel):
    value: Name
    system: Name
    scale: str | None = Field(default=None, max_length=100)

class Coursework(Entry):
    name: Name

class Education(DatedEntry):
    institution: str = Field(default="", max_length=200)
    degree: str = Field(default="", max_length=200)
    field_of_study: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=300)
    expected_graduation: PartialDate | None = None
    score: AcademicScore | None = None
    coursework: list[Coursework] = Field(default_factory=list)
    description: Text = ""
    bullets: list[Bullet] = Field(default_factory=list)

    @model_validator(mode="after")
    def graduation(self):
        validate_range(self.start_date, self.expected_graduation)
        if self.end_date and self.expected_graduation:
            raise ValueError("Use actual end date or expected graduation, not both")
        return self

class Evidence(ValueModel):
    entry_id: UUID
    note: Text = ""

class Skill(Entry):
    # Preserve the user's spelling; normalization is a separate future concern.
    name: Name
    category: str | None = Field(default=None, max_length=100)
    canonical_skill_id: str | None = Field(default=None, max_length=100)
    evidence: list[Evidence] = Field(default_factory=list)

class Project(DatedEntry):
    name: str = Field(default="", max_length=200)
    description: Text = ""
    contributions: list[Bullet] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)
    technologies: list[Name] = Field(default_factory=list)
    links: list[ProfessionalLink] = Field(default_factory=list)
    status: str | None = Field(default=None, max_length=100)

class Certification(Entry):
    name: Name
    issuer: str = Field(default="", max_length=200)
    issue_date: PartialDate | None = None
    expiration_date: PartialDate | None = None
    credential_id: str | None = Field(default=None, max_length=200)
    credential_url: HttpUrl | None = None

    @model_validator(mode="after")
    def dates(self):
        validate_range(self.issue_date, self.expiration_date)
        return self

class Achievement(Entry):
    title: Name
    description: Text = ""
    organization: str = Field(default="", max_length=200)
    date: PartialDate | None = None

class AdditionalEntry(DatedEntry):
    title: str = Field(default="", max_length=200)
    organization: str = Field(default="", max_length=200)
    description: Text = ""
    bullets: list[Bullet] = Field(default_factory=list)
    links: list[ProfessionalLink] = Field(default_factory=list)

class Language(Entry):
    name: Name
    proficiency: str | None = Field(default=None, max_length=100)

class CustomSection(Entry):
    title: Name
    description: Text = ""
    entries: list[AdditionalEntry] = Field(default_factory=list)
