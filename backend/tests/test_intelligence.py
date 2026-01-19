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
