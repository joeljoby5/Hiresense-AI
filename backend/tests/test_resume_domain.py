import json
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.domain.resume.models import ResumeDocument, serialize_document, deserialize_document
from app.domain.resume.common import PartialDate


def populated():
    return {
        "personal_information": {"full_name": "Synthetic Professional", "email": "synthetic@example.org",
                                 "phone": "+44 (0) 20 1234 5678", "links": [{"kind": "github", "url": "https://github.com/example"}]},
        "experience": [{"organization": "Example Lab", "position": "Engineer", "start_date": {"year": 2020},
                        "end_date": {"year": 2022, "month": 5}, "bullets": [{"text": "Built a synthetic fixture"}]}],
        "education": [{"institution": "Example Institute", "score": {"value": "82", "system": "percentage"},
                       "ongoing": True, "expected_graduation": {"year": 2027}}],
        "skills": [{"name": "TypeScript", "category": "Engineering"}],
        "projects": [{"name": "Synthetic Project", "contributions": [{"text": "Implemented validation"}]}],
        "certifications": [{"name": "Synthetic Credential", "issue_date": {"year": 2024}}],
        "achievements": [{"title": "Synthetic Award"}],
        "publications": [{"title": "Example Publication"}],
        "research": [{"title": "Example Study"}],
        "volunteer_experience": [{"title": "Mentor"}],
        "leadership_experience": [{"title": "Coordinator"}],
        "languages": [{"name": "English", "proficiency": "Professional"}],
        "relevant_coursework": [{"name": "Algorithms"}],
        "custom_sections": [{"title": "Community", "entries": [{"title": "Workshop"}]}],
    }


def test_empty_draft_and_defaults_are_independent():
    first, second = ResumeDocument(), ResumeDocument()
    assert first.schema_version == 1
    first.section_order.append("skills")
    first.presentation_settings.margins.top = 25
    assert second.section_order == []
    assert second.presentation_settings.margins.top == 20


def test_populated_roundtrip_unicode_and_identifiers():
    payload = populated()
    # Explicit escapes keep the fixture independent of terminal encoding.
    payload["personal_information"]["full_name"] = "Jos\u00e9 \u674e"
    document = ResumeDocument.model_validate(payload)
    serialized = serialize_document(document)
    rebuilt = deserialize_document(json.loads(json.dumps(serialized, ensure_ascii=False)))
    assert rebuilt == document
    assert rebuilt.experience[0].id == document.experience[0].id
    assert rebuilt.experience[0].bullets[0].id == document.experience[0].bullets[0].id
    assert rebuilt.custom_sections[0].entries[0].id == document.custom_sections[0].entries[0].id


@pytest.mark.parametrize("payload", [
    {"schema_version": 2},
    {"schema_version": True},
    {"schema_version": 1.0},
    {"experience": [{"start_date": {"year": True}}]},
    {"unknown": "must not disappear"},
    {"personal_information": {"email": "invalid"}},
    {"personal_information": {"links": [{"url": "javascript:alert(1)"}]}},
    {"personal_information": {"links": [{"url": "ftp://example.org"}]}},
    {"skills": [{"name": "   "}]},
    {"experience": [{"start_date": {"year": 2024, "month": 13}}]},
    {"experience": [{"start_date": {"year": 2025}, "end_date": {"year": 2024}}]},
    {"experience": [{"start_date": {"year": 2024, "month": 6}, "end_date": {"year": 2024, "month": 5}}]},
    {"experience": [{"ongoing": True, "end_date": {"year": 2024}}]},
    {"education": [{"start_date": {"year": 2025}, "expected_graduation": {"year": 2024}}]},
    {"education": [{"end_date": {"year": 2025}, "expected_graduation": {"year": 2025}}]},
    {"certifications": [{"name": "Example", "issue_date": {"year": 2025}, "expiration_date": {"year": 2024}}]},
    {"presentation_settings": {"page_size": "A3"}},
    {"presentation_settings": {"font_size": 100}},
    {"presentation_settings": {"line_spacing": float("nan")}},
    {"presentation_settings": {"margins": {"left": -1}}},
    {"presentation_settings": {"accent_color": "red"}},
    {"section_order": ["skills", "skills"]},
    {"section_order": ["nonexistent"]},
    {"section_configuration": [{"section_id": "unknown"}]},
    {"section_configuration": [{"section_id": "skills"}, {"section_id": "skills"}]},
    {"custom_sections": [{"title": ""}]},
    {"custom_sections": [{"title": "Example", "entries": [{"html": "unsafe"}]}]},
    {"custom_sections": [{"title": "Example", "description": "<script>alert(1)</script>"}]},
    {"skills": [{"name": "Example", "evidence": [{"entry_id": str(uuid4())}]}]},
])
def test_invalid_nested_documents(payload):
    with pytest.raises(ValidationError):
        ResumeDocument.model_validate(payload)


def test_duplicate_identifiers_across_sections():
    same_id = uuid4()
    with pytest.raises(ValidationError, match="Duplicate entry identifier"):
        ResumeDocument.model_validate({"skills": [{"id": same_id, "name": "Python"}],
                                       "projects": [{"id": same_id, "name": "Example"}]})


def test_partial_dates_do_not_invent_chronology():
    assert PartialDate(year=2024).month is None
    ResumeDocument.model_validate({"experience": [{"start_date": {"year": 2024, "month": 12},
                                                  "end_date": {"year": 2024}}]})


def test_custom_section_references_and_default_order():
    section_id = str(uuid4())
    doc = ResumeDocument.model_validate({"custom_sections": [{"id": section_id, "title": "Community"}],
        "section_order": [section_id, "skills"],
        "section_configuration": [{"section_id": section_id, "visible": False, "title": "Other work"}]})
    assert doc.ordered_section_ids()[:2] == [section_id, "skills"]
    assert len(doc.ordered_section_ids()) == len(set(doc.ordered_section_ids()))
    assert "education" in doc.ordered_section_ids()


def test_mutated_document_revalidated_before_storage():
    doc = ResumeDocument()
    doc.section_order.append("unknown")
    with pytest.raises(ValidationError):
        serialize_document(doc)
