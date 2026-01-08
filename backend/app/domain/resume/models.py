from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from app.domain.resume.common import Entry, Text, ValueModel
from app.domain.resume.presentation import PresentationSettings, SectionConfiguration
from app.domain.resume.sections import (
    Achievement, AdditionalEntry, Certification, Coursework, CustomSection, Education,
    Experience, Language, PersonalInformation, Project, Skill,
)

BUILTIN_SECTIONS = (
    "personal_information", "professional_summary", "career_objective", "experience",
    "education", "skills", "projects", "certifications", "achievements", "publications",
    "research", "volunteer_experience", "leadership_experience", "languages", "relevant_coursework",
)

class ResumeDocument(ValueModel):
    schema_version: Literal[1] = 1
    language: str = Field(default="en", pattern=r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")
    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    professional_summary: Text = ""
    career_objective: Text = ""
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
    publications: list[AdditionalEntry] = Field(default_factory=list)
    research: list[AdditionalEntry] = Field(default_factory=list)
    volunteer_experience: list[AdditionalEntry] = Field(default_factory=list)
    leadership_experience: list[AdditionalEntry] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    relevant_coursework: list[Coursework] = Field(default_factory=list)
    custom_sections: list[CustomSection] = Field(default_factory=list)
    section_order: list[str] = Field(default_factory=list)
    section_configuration: list[SectionConfiguration] = Field(default_factory=list)
    presentation_settings: PresentationSettings = Field(default_factory=PresentationSettings)

    @field_validator("schema_version", mode="before")
    @classmethod
    def supported_schema(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported resume schema version; supported version is 1")
        return value

    @model_validator(mode="after")
    def references(self):
        seen: set[UUID] = set()
        def visit(value):
            if isinstance(value, Entry):
                if value.id in seen:
                    raise ValueError("Duplicate entry identifier")
                seen.add(value.id)
            if isinstance(value, BaseModel):
                for name in type(value).model_fields:
                    visit(getattr(value, name))
            elif isinstance(value, list):
                for item in value:
                    visit(item)
        visit(self)
        if any(e.entry_id not in seen for skill in self.skills for e in skill.evidence):
            raise ValueError("Skill evidence must reference an existing entry")
        valid = set(BUILTIN_SECTIONS) | {str(section.id) for section in self.custom_sections}
        configured = [item.section_id for item in self.section_configuration]
        for refs in (self.section_order, configured):
            if len(refs) != len(set(refs)) or not set(refs) <= valid:
                raise ValueError("Section references must be unique and refer to existing sections")
        return self

    def ordered_section_ids(self) -> list[str]:
        all_ids = [*BUILTIN_SECTIONS, *(str(item.id) for item in self.custom_sections)]
        return [*self.section_order, *(key for key in all_ids if key not in self.section_order)]

def serialize_document(document: ResumeDocument) -> dict:
    # Revalidate even already-built/mutated models; JSON replacement is always explicit.
    return ResumeDocument.model_validate(document.model_dump(mode="json")).model_dump(mode="json")

def deserialize_document(content: dict) -> ResumeDocument:
    return ResumeDocument.model_validate(content)
