from io import BytesIO
import re
from uuid import uuid4

from docx import Document
import pytest
from pypdf import PdfReader

from app.api.identity import resolve_owner
from app.documents.render import ExportContentError, export_document
from app.domain.resume.models import ResumeDocument
from test_resume_api import api
from test_resume_services import services


SYNTHETIC = {
    "personal_information": {"full_name": "Zoë Candidate", "email": "candidate@example.org",
                             "links": [{"label": "Portfolio", "url": "https://example.org/portfolio"}]},
    "experience": [{"organization": "Example Studio", "position": "Developer",
                    "bullets": [{"text": "Improved accessibility & navigation."}]}],
    "education": [{"institution": "Example College", "degree": "Computer Science"}],
    "skills": [{"name": "C++"}],
    "projects": [{"name": "Synthetic dashboard"}],
    "certifications": [{"name": "Example credential"}],
    "professional_summary": "Visible summary",
    "career_objective": "Hidden objective marker",
    "section_order": ["personal_information", "skills", "experience"],
    "section_configuration": [{"section_id": "career_objective", "visible": False}],
    "presentation_settings": {"page_size": "Letter", "template_id": "modern-technical"},
}


@pytest.mark.parametrize("format", ["pdf", "docx", "txt", "json"])
def test_content_round_trip(format):
    document = ResumeDocument.model_validate(SYNTHETIC)
    result = export_document(document, format)
    if format == "json":
        assert ResumeDocument.model_validate_json(result) == document
        return
    if format == "pdf":
        pdf = PdfReader(BytesIO(result))
        assert pdf.pages[0].mediabox.width == 612
        assert pdf.pages[0]["/Annots"][0].get_object()["/A"]["/URI"] == "https://example.org/portfolio"
        extracted = "\n".join(page.extract_text() for page in pdf.pages)
    elif format == "docx":
        doc = Document(BytesIO(result))
        assert doc.sections[0].page_width.inches == 8.5
        assert any(paragraph.style.name == "List Bullet" for paragraph in doc.paragraphs)
        assert any(paragraph.style.name == "Heading 1" for paragraph in doc.paragraphs)
        assert any(hyperlink.url == "https://example.org/portfolio" for p in doc.paragraphs for hyperlink in p.hyperlinks)
        extracted = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    else:
        extracted = result.decode()
    extracted = re.sub(r"\s+", " ", extracted)
    for value in ("Zoë Candidate", "candidate@example.org", "Portfolio", "Example Studio",
                  "Improved accessibility & navigation.", "Example College", "C++",
                  "Synthetic dashboard", "Example credential", "Visible summary"):
        assert value in extracted
    assert extracted.index("Skills") < extracted.index("Experience")
    assert "Hidden objective marker" not in extracted


def test_pdf_paginates_without_truncating_last_item():
    document = ResumeDocument.model_validate({
        "experience": [{"position": f"Synthetic position {index}", "description": "Readable text " * 35}
                       for index in range(35)],
    })
    pages = PdfReader(BytesIO(export_document(document, "pdf"))).pages
    assert len(pages) > 1
    assert "Synthetic position 34" in pages[-1].extract_text()


def test_incompatible_unicode_is_explicit():
    doc = ResumeDocument(professional_summary="李")
    with pytest.raises(ExportContentError, match="font does not support"):
        export_document(doc, "pdf")
    assert "李" in export_document(doc, "txt").decode()


def test_artifacts_are_revision_specific_and_owner_scoped(api):
    client, a, b = api
    prefix = "/api/v1/resumes"
    resume = client.post(prefix, json={"title": "Synthetic", "content": SYNTHETIC})
    base = resume.headers["location"]
    checkpoint = client.post(base + "/versions", json={"expected_revision": 1}).json()
    assert client.patch(base, json={"expected_revision": 1, "content": {"professional_summary": "New summary"}}).status_code == 200
    endpoint = base + "/exports"
    save = client.post(endpoint, json={"format": "txt", "expected_revision": 1})
    assert save.status_code == 409
    for body in ({"format": "txt"}, {"format": "bad", "expected_revision": 2},
                 {"format": "txt", "expected_revision": 2, "version_id": checkpoint["id"]}):
        assert client.post(endpoint, json=body).status_code == 422
    assert client.post(endpoint, json={"format": "txt", "version_id": str(uuid4())}).status_code == 404
    old = client.post(endpoint, json={"format": "txt", "version_id": checkpoint["id"]})
    assert old.status_code == 201, old.text
    assert old.json()["source_revision"] == 1
    assert old.json()["source_version_id"] == checkpoint["id"]
    current = client.post(endpoint, json={"format": "txt", "expected_revision": 2})
    assert current.status_code == 201, current.text
    download = client.get(old.headers["location"])
    assert download.status_code == 200
    assert download.headers["cache-control"] == "private, no-store"
    assert download.headers["content-disposition"] == 'attachment; filename="resume-r1.txt"'
    assert "Visible summary" in download.text and "New summary" not in download.text
    assert "New summary" in client.get(current.headers["location"]).text
    assert len(client.get(endpoint).json()) == 2
    client.app.dependency_overrides[resolve_owner] = lambda: b.owner_id
    assert client.get(endpoint).status_code == 404
    assert client.get(old.headers["location"]).status_code == 404
    assert client.post(endpoint, json={"format": "txt", "expected_revision": 2}).status_code == 404
    client.app.dependency_overrides[resolve_owner] = lambda: a.owner_id
    assert client.delete(base, params={"expected_revision": 2}).status_code == 204
    assert client.get(old.headers["location"]).status_code == 404


def test_archive_retention_is_owner_scoped(api, monkeypatch):
    client, a, b = api
    monkeypatch.setattr("app.repositories.exports.OWNER_EXPORT_LIMIT", 2)
    prefix = "/api/v1/resumes"
    client.app.dependency_overrides[resolve_owner] = lambda: b.owner_id
    foreign = client.post(prefix, json={"title": "Other owner"}).headers["location"] + "/exports"
    foreign_file = client.post(foreign, json={"format": "json", "expected_revision": 1}).headers["location"]
    client.app.dependency_overrides[resolve_owner] = lambda: a.owner_id
    endpoint = client.post(prefix, json={"title": "Retention check"}).headers["location"] + "/exports"
    files = [client.post(endpoint, json={"format": "txt", "expected_revision": 1}).headers["location"] for _ in range(3)]
    assert client.get(files[0]).status_code == 404
    assert all(client.get(path).status_code == 200 for path in files[1:])
    client.app.dependency_overrides[resolve_owner] = lambda: b.owner_id
    assert client.get(foreign_file).status_code == 200
