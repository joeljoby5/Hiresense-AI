from typing import Literal
from pydantic import Field
from app.domain.resume.common import ValueModel

class Margins(ValueModel):
    top: float = Field(default=20, ge=5, le=50, allow_inf_nan=False)
    right: float = Field(default=20, ge=5, le=50, allow_inf_nan=False)
    bottom: float = Field(default=20, ge=5, le=50, allow_inf_nan=False)
    left: float = Field(default=20, ge=5, le=50, allow_inf_nan=False)

class PresentationSettings(ValueModel):
    template_id: str = Field(default="default", pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    page_size: Literal["A4", "Letter"] = "A4"
    font_family: Literal["Arial", "Calibri", "Times New Roman", "Georgia", "Helvetica"] = "Arial"
    font_size: float = Field(default=11, ge=8, le=24, allow_inf_nan=False)
    line_spacing: float = Field(default=1.15, ge=1, le=2.5, allow_inf_nan=False)
    section_spacing: float = Field(default=8, ge=0, le=40, allow_inf_nan=False)
    margins: Margins = Field(default_factory=Margins)
    accent_color: str = Field(default="#243B53", pattern=r"^#[0-9a-fA-F]{6}$")

class SectionConfiguration(ValueModel):
    section_id: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    visible: bool = True
