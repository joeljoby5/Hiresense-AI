from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Literal

from app.domain.intelligence.lexical import LEXICAL_VERSION, lexical_similarity
from app.domain.intelligence.requirements import Extraction
from app.domain.intelligence.taxonomy import find_skills
from app.domain.resume.models import ResumeDocument

ALGORITHM_VERSION = "ats-structured-1"
CONFIGURATION_VERSION = "weights-1"
KNOWN_TEMPLATES = frozenset({"default", "professional-classic", "minimalist", "modern-technical", "graduate", "software", "compact"})
EXPERIENTIAL = frozenset({"experience", "projects", "research", "volunteer_experience", "leadership_experience"})
SOURCES = {
    "skills": ("name",),
    "experience": ("position", "description", "technologies", "bullets"),
    "projects": ("name", "description", "technologies", "bullets", "contributions"),
    "education": ("field_of_study", "coursework"),
    "certifications": ("name",),
    "research": ("title", "description", "bullets"),
    "publications": ("title", "description", "bullets"),
    "leadership_experience": ("title", "description", "bullets"),
    "volunteer_experience": ("title", "description", "bullets"),
}


@dataclass(frozen=True)
class Component:
    name: str
    weight: int
    score: float | None
    finding: str
    status: Literal["evaluated", "unknown", "not_applicable"] = "evaluated"


@dataclass(frozen=True)
class Dimension:
    score: float | None
    coverage: int
    provisional: bool
    components: tuple[Component, ...]


@dataclass(frozen=True)
class Evidence:
    section: str
    entry_id: str | None


@dataclass(frozen=True)
class SkillFinding:
    priority: str
    alternatives: tuple[str, ...]
    status: Literal["matched", "not_evidenced"]
    evidence: dict[str, tuple[Evidence, ...]]
    source_text: str


@dataclass(frozen=True)
class Analysis:
    algorithm_version: str
    configuration_version: str
    lexical_version: str
    readability: Dimension
    compatibility: Dimension
    skills: tuple[SkillFinding, ...]
    skill_names: dict[str, str]
    notices: tuple[str, ...]


def dimension(parts: tuple[Component, ...], threshold: int, provisional: bool = False) -> Dimension:
    evaluated = [part for part in parts if part.score is not None]
    coverage = sum(part.weight for part in evaluated)
    score = round(sum(part.score * part.weight for part in evaluated) / coverage, 1) if coverage >= threshold else None
    return Dimension(score, coverage, provisional or coverage < 100, parts)


def readability(document: ResumeDocument) -> Dimension:
    configurations = {config.section_id: config for config in document.section_configuration}
    visible = [key for key in document.ordered_section_ids() if not (key in configurations and not configurations[key].visible)]
    data = document.model_dump(mode="json")
    custom = {str(item.id): item for item in document.custom_sections}
    populated = [key for key in visible if key != "personal_information" and (data.get(key) or key in custom)]
    default_headings = sum(key in data and not (key in configurations and configurations[key].title) for key in populated)
    headings = 100 * default_headings / len(populated) if populated else None
    contact = document.personal_information
    contact_score = 100 * (bool(contact.email) + bool(contact.phone.strip())) / 2 if "personal_information" in visible else 0
    dated = [entry for key in ("experience", "education") if key in visible for entry in data[key]]
    dated_count = sum(bool(entry["start_date"] and (entry["ongoing"] or entry.get("end_date") or entry.get("expected_graduation")))
                      for entry in dated)
    date_score = 100 * dated_count / len(dated) if dated else None
    settings = document.presentation_settings
    layout = 100 if settings.template_id in KNOWN_TEMPLATES and settings.font_size >= 9 else None
    return dimension((
        Component("Text extractability", 25, None, "Requires reading a generated or imported file.", "unknown"),
        Component("Section headings", 20, headings, "Estimates recognizable default headings for visible populated sections.",
                  "evaluated" if headings is not None else "not_applicable"),
        Component("Logical reading order", 15, None, "File-level reading order requires extraction.", "unknown"),
        Component("Contact accessibility", 15, contact_score, "Checks whether a visible contact section contains an email and phone."),
        Component("Layout settings", 15, layout, "Checks for a known single-column template with a body font of at least 9 points.",
                  "evaluated" if layout is not None else "unknown"),
        Component("Date completeness", 10, date_score, "Checks visible dated entries for a start and end, expected graduation or ongoing status.",
                  "evaluated" if date_score is not None else "not_applicable"),
    ), 50, provisional=True)


def text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from text_values(item)
    elif isinstance(value, dict):
        for key in ("text", "name"):
            if key in value:
                yield from text_values(value[key])


def skill_evidence(document: ResumeDocument) -> tuple[dict[str, list[Evidence]], Counter]:
    content = document.model_dump(mode="json")
    hidden = {config.section_id for config in document.section_configuration if not config.visible}
    evidence: dict[str, list[Evidence]] = defaultdict(list)
    counts = Counter()
    for section, fields in SOURCES.items():
        if section in hidden:
            continue
        for entry in content[section]:
            skills = {mention.skill.id for field in fields for value in text_values(entry.get(field)) for mention in find_skills(value)}
            for skill in sorted(skills):
                counts[skill] += 1
                if sum(item.section == section for item in evidence[skill]) < 4:
                    evidence[skill].append(Evidence(section, entry["id"]))
    for section in ("professional_summary", "career_objective"):
        if section in hidden:
            continue
        for skill in sorted({mention.skill.id for mention in find_skills(content[section])}):
            counts[skill] += 1
            evidence[skill].append(Evidence(section, None))
    return evidence, counts


def run_analysis(document: ResumeDocument, extraction: Extraction) -> Analysis:
    evidence, candidate_terms = skill_evidence(document)
    findings = []
    target_terms = Counter()
    for requirement in extraction.requirements:
        if requirement.kind != "skill" or requirement.priority == "optional":
            continue
        positive = {skill: tuple(evidence[skill]) for skill in requirement.alternatives if skill in evidence}
        findings.append(SkillFinding(requirement.priority, requirement.alternatives,
                                     "matched" if positive else "not_evidenced", positive, requirement.evidence))
        if requirement.priority in {"mandatory", "preferred"}:
            target_terms.update(requirement.alternatives)
    mandatory = [item for item in findings if item.priority == "mandatory"]
    relevant = [item for item in findings if item.priority in {"mandatory", "preferred"}]
    required_score = 100 * sum(item.status == "matched" for item in mandatory) / len(mandatory) if mandatory else None
    relevance_score = 100 * lexical_similarity(
        " ".join(term for term, count in candidate_terms.items() for _ in range(min(count, 3))),
        " ".join(term for term, count in target_terms.items() for _ in range(min(count, 3))),
    ) if target_terms else None
    documented = sum(any(e.section in EXPERIENTIAL for matches in item.evidence.values() for e in matches) for item in relevant)
    experience_score = 100 * documented / len(relevant) if relevant else None
    alignment = 100 * sum(item.status == "matched" for item in relevant) / len(relevant) if relevant else None
    other = any(item.kind in {"experience", "education", "certification"} and item.priority in {"mandatory", "preferred"}
                for item in extraction.requirements)
    unknown_target = "unknown" if not relevant else "evaluated"
    result = dimension((
        Component("Required skill coverage", 30, required_score, "One evidenced alternative satisfies a mandatory skill group.",
                  "evaluated" if mandatory else "not_applicable"),
        Component("Lexical relevance", 25, relevance_score, "TF-IDF cosine similarity across recognized professional skill terms.", unknown_target),
        Component("Experience and project evidence", 20, experience_score, "Counts groups with evidence in work, projects, research or leadership.", unknown_target),
        Component("Keyword alignment", 15, alignment, "Counts recognized required and preferred skill groups evidenced anywhere in the resume.", unknown_target),
        Component("Other qualifications", 10, None, "Education equivalence, certifications and duration require manual review.",
                  "unknown" if other else "not_applicable"),
    ), 75)
    return Analysis(ALGORITHM_VERSION, CONFIGURATION_VERSION, LEXICAL_VERSION, readability(document), result,
                    tuple(findings), extraction.skill_names, (
                        "HireSense scores are experimental estimates. Review the evidence against the target role.",
                        "A requirement marked not evidenced may still be part of your experience. Add details only when accurate.",
                    ))
