import json
from io import BytesIO
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal
from xml.sax.saxutils import escape, quoteattr

import reportlab
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.shared import Mm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.documents.layout import Line, document_lines
from app.domain.resume.models import ResumeDocument

ExportFormat = Literal["pdf", "docx", "txt", "json"]
MEDIA_TYPES: dict[ExportFormat, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
    "json": "application/json",
}
MAX_EXPORT_BYTES = 2 * 1024 * 1024
_renderer = BoundedSemaphore(1)
_font_dir = Path(reportlab.__file__).parent / "fonts"
for name, file in (("ResumeText", "Vera.ttf"), ("ResumeBold", "VeraBd.ttf")):
    pdfmetrics.registerFont(TTFont(name, str(_font_dir / file)))


class ExportContentError(Exception):
    pass


class ExportBusyError(Exception):
    pass


def validate_lines(lines: list[Line]):
    if len(lines) > 1500 or sum(len(line.text) for line in lines) > 120_000:
        raise ExportContentError("The resume exceeds document export limits.")
    if any(any(ord(character) < 32 and character not in "\t\n\r" or ord(character) in (0xFFFE, 0xFFFF)
               for character in line.text) for line in lines):
        raise ExportContentError("Remove unsupported control characters before exporting.")


def export_document(document: ResumeDocument, output: ExportFormat) -> bytes:
    if not _renderer.acquire(blocking=False):
        raise ExportBusyError()
    try:
        if output == "json":
            data = (json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n").encode()
        else:
            lines = document_lines(document)
            validate_lines(lines)
            if output == "txt":
                data = ("\n".join(("\n" if line.role == "heading" else "• " if line.role == "bullet" else "") + line.text
                                  for line in lines).lstrip("\n") + "\n").encode()
            elif output == "pdf":
                data = render_pdf(document, lines)
            else:
                data = render_docx(document, lines)
        if len(data) > MAX_EXPORT_BYTES:
            raise ExportContentError("The generated document exceeds the size limit.")
        return data
    finally:
        _renderer.release()


def render_pdf(document: ResumeDocument, lines: list[Line]) -> bytes:
    buffer = BytesIO()
    settings = document.presentation_settings
    margin = settings.margins
    template = settings.template_id
    accent = colors.HexColor(settings.accent_color)
    page = SimpleDocTemplate(buffer, pagesize=LETTER if settings.page_size == "Letter" else A4,
                             leftMargin=margin.left * mm, rightMargin=margin.right * mm,
                             topMargin=margin.top * mm, bottomMargin=margin.bottom * mm,
                             title="HireSense AI Resume", author="")
    base = ParagraphStyle("Resume", fontName="ResumeText", fontSize=settings.font_size,
                          leading=settings.font_size * settings.line_spacing, spaceAfter=2, splitLongWords=True)
    styles = {
        "name": ParagraphStyle("Name", parent=base, fontName="ResumeBold", textColor=accent,
                               fontSize=settings.font_size * (1.6 if template == "compact" else 1.9),
                               leading=settings.font_size * 2.05, spaceAfter=4, keepWithNext=True,
                               **({"alignment": TA_CENTER} if template in ("default", "professional-classic") else {})),
        "heading": ParagraphStyle("Heading", parent=base, fontName="ResumeBold", textColor=accent,
                                  spaceBefore=settings.section_spacing, keepWithNext=True,
                                  **({"backColor": colors.HexColor("#EEF2F6")} if template == "modern-technical" else {})),
        "entry": ParagraphStyle("Entry", parent=base, fontName="ResumeBold", spaceBefore=3),
        "bullet": ParagraphStyle("Bullet", parent=base, leftIndent=12, bulletIndent=2, bulletFontName="ResumeText"),
        "link": ParagraphStyle("Link", parent=base, textColor=accent),
        "text": base,
    }
    paragraphs = []
    for line in lines:
        style = styles[line.role]
        glyphs = pdfmetrics.getFont(style.fontName).face.charToGlyph
        if any(ord(character) not in glyphs for character in line.text if character not in "\t\n\r"):
            raise ExportContentError("The PDF font does not support some characters. Choose DOCX, TXT or JSON.")
        value = escape(line.text).replace("\n", "<br/>")
        if line.url:
            value = f"<link href={quoteattr(line.url)}><u>{value}</u></link>"
        paragraphs.append(Paragraph(value, style, bulletText="•" if line.role == "bullet" else None))
    page.build(paragraphs or [Paragraph(" ", base)])
    return buffer.getvalue()


def render_docx(document: ResumeDocument, lines: list[Line]) -> bytes:
    output = BytesIO()
    settings = document.presentation_settings
    file = Document()
    file.core_properties.title = "HireSense AI Resume"
    file.core_properties.author = ""
    section = file.sections[0]
    width, height = (215.9, 279.4) if settings.page_size == "Letter" else (210, 297)
    section.page_width, section.page_height = Mm(width), Mm(height)
    for side in ("top", "right", "bottom", "left"):
        setattr(section, side + "_margin", Mm(getattr(settings.margins, side)))
    styles = {"name": "Title", "heading": "Heading 1", "entry": "Heading 2",
              "text": "Normal", "bullet": "List Bullet", "link": "Normal"}
    for name in set(styles.values()):
        style = file.styles[name]
        style.font.name = settings.font_family
        style.font.size = Pt(settings.font_size * (1.9 if name == "Title" else 1))
        style.paragraph_format.line_spacing = settings.line_spacing
        style.paragraph_format.space_after = Pt(3)
        if name in ("Title", "Heading 1"):
            style.font.color.rgb = RGBColor.from_string(settings.accent_color[1:])
    file.styles["Heading 1"].paragraph_format.space_before = Pt(settings.section_spacing)
    if settings.template_id in ("default", "professional-classic"):
        file.styles["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for line in lines:
        paragraph = file.add_paragraph(style=styles[line.role])
        if line.url:
            run = paragraph.add_run(line.text)
            run.underline = True
            hyperlink = OxmlElement("w:hyperlink")
            hyperlink.set(qn("r:id"), paragraph.part.relate_to(line.url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
            hyperlink.append(run._r)
            paragraph._p.append(hyperlink)
        else:
            paragraph.add_run(line.text)
    file.save(output)
    return output.getvalue()
