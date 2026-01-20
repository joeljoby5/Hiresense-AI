import pytest

from app.domain.intelligence.lexical import lexical_similarity, terms, tokens
from app.domain.intelligence.requirements import extract_requirements
from app.domain.intelligence.taxonomy import SKILLS, find_skills


def test_aliases_and_token_boundaries():
    assert len({skill.id for skill in SKILLS}) == len(SKILLS)
    phrase = "JavaScript, Java, C++, C#, .NET, Node.js, React Native, React, PostgreSQL, Postgres, CI/CD and AWS."
    assert [entry.skill.id for entry in find_skills(phrase)] == [
        "javascript", "java", "cpp", "csharp", "dotnet", "node-js", "react-native", "react",
        "postgresql", "postgresql", "ci-cd", "aws",
    ]
    assert not find_skills("Go to the cafeteria for vitamin C. I like CO2.")
    assert [entry.skill.id for entry in find_skills("embedded programming in C")] == ["c"]
    assert [entry.skill.id for entry in find_skills("Ｐｙｔｈｏｎ")] == ["python"]


def test_lexical_similarity_edges_and_term_frequency_cap():
    assert tokens("An AWS, CI/CD, C++, .NET and Node.js") == ["aws", "ci/cd", "c++", ".net", "node.js"]
    assert lexical_similarity("", "Python") == 0
    assert lexical_similarity("Java", "JavaScript") == 0
    assert lexical_similarity("Python, Java", "Java Python") == pytest.approx(1)
    assert lexical_similarity("Python Git Go", "Python Django") == lexical_similarity("Python Django", "Python Git Go")
    assert lexical_similarity("Python " * 100 + "SQL", "Python database") == lexical_similarity("Python " * 3 + "SQL", "Python database")
    assert terms("AWS AWS AWS Docker", 1) == ["aws"]


def test_job_extraction_keeps_source_spans_and_alternatives():
    source = """Minimum qualifications:
 - Python, Java, or Go.
 - 3+ years of experience with PostgreSQL.
Preferred: AWS and CI/CD.
Docker experience is optional.
No need for TensorFlow.
Responsibilities:
 Help maintain a dashboard.
"""
    result = extract_requirements(source, "Senior Backend Engineer")
    assert result.seniority == "senior" and result.role_category == "backend"
    items = result.requirements
    for item in items:
        assert source[item.start:item.end] == item.evidence
    assert items[0].alternatives == ("python", "java", "go") and items[0].priority == "mandatory"
    assert any(item.kind == "experience" and item.years == 3 for item in items)
    assert any(item.alternatives == ("aws",) and item.priority == "preferred" for item in items)
    assert any(item.alternatives == ("docker",) and item.priority == "optional" for item in items)
    assert not any("tensorflow" in item.alternatives for item in items)
    assert items[-1].kind == "responsibility"
    assert extract_requirements("").requirements == ()

def test_ats_keeps_readability_separate_and_preserves_alternative_groups():
    from app.domain.intelligence.ats import run_analysis
    from app.domain.resume.models import ResumeDocument

    job = extract_requirements("Required: Python or Java. Preferred: AWS. Master's degree preferred.")
    draft = ResumeDocument.model_validate({
        "skills": [{"name": "Python"}],
        "projects": [{"name": "Example", "technologies": ["Python"]}],
        "personal_information": {"email": "candidate@example.org", "phone": "555-0100"},
    })
    report = run_analysis(draft, job)
    assert report.compatibility.coverage == 90 and report.compatibility.provisional
    assert report.compatibility.components[0].score == 100
    assert report.readability.score is not None and report.readability.coverage == 50
    assert report.readability.components[0].status == "unknown"
    assert report.skills[0].alternatives == ("python", "java") and report.skills[0].status == "matched"
    assert report.skills[1].status == "not_evidenced"
    assert any(evidence.section == "projects" for evidence in report.skills[0].evidence["python"])
    altered = draft.model_copy(deep=True)
    altered.personal_information.full_name = "AWS Java"
    assert run_analysis(altered, job).compatibility == report.compatibility
    assert run_analysis(altered, job).skills == report.skills


def test_ats_withholds_scores_for_unknown_requirements():
    from app.domain.intelligence.ats import run_analysis
    from app.domain.resume.models import ResumeDocument

    outcome = run_analysis(ResumeDocument(), extract_requirements("We value an inclusive workplace."))
    assert outcome.compatibility.score is None and outcome.compatibility.coverage == 0
    assert outcome.readability.score is None
    target = extract_requirements("Required: PostgreSQL.")
    outcome = run_analysis(ResumeDocument(), target)
    assert outcome.compatibility.score == 0 and outcome.compatibility.coverage == 90
