from dataclasses import dataclass
import re
from typing import Literal

from app.domain.intelligence.taxonomy import SKILLS, TAXONOMY_VERSION, find_skills, normalize

EXTRACTION_VERSION = "job-requirements-1"
Priority = Literal["mandatory", "preferred", "optional", "ambiguous"]
Kind = Literal["skill", "experience", "education", "certification", "responsibility"]
_REQUIRED = re.compile(r"\b(?:required|must(?: have)?|minimum|essential|need(?:ed)?|requirements?|qualifications)\b", re.I)
_PREFERRED = re.compile(r"\b(?:preferred|desirable|nice to have|bonus|advantage|plus)\b", re.I)
_OPTIONAL = re.compile(r"\b(?:optional|not required|no [^.;]{1,80} required)\b", re.I)
_NEGATED = re.compile(r"\b(?:no need for|not(?: currently)? using|no requirement for|without requiring|do not require)\b", re.I)
_YEARS = re.compile(r"\b([1-9]\d?)\s*\+?\s*(?:years?|yrs?)\b", re.I)
_EDUCATION = re.compile(r"\b(?:bachelor|master|doctorate|ph\.?d|associate degree|university degree)\b", re.I)
_CERTIFICATION = re.compile(r"\b(?:certification|certified|PMP|CISSP|CCNA)\b", re.I)
_RESPONSIBILITIES = re.compile(r"^(?:key |job )?(?:responsibilities|duties|what you will do)$", re.I)
_CLAUSE = re.compile(r"[^\r\n;]+?(?:\.(?=\s|$)|(?=[\r\n;]|$))")
_ALT = re.compile(r"\s*,?\s*(?:and/)?or\s+(?:in\s+)?", re.I)
_COMMA = re.compile(r"\s*,\s*")


@dataclass(frozen=True)
class Requirement:
    kind: Kind
    priority: Priority
    alternatives: tuple[str, ...]
    evidence: str
    start: int
    end: int
    years: int | None = None


@dataclass(frozen=True)
class Extraction:
    extractor_version: str
    taxonomy_version: str
    seniority: str | None
    role_category: str | None
    requirements: tuple[Requirement, ...]
    skill_names: dict[str, str]


def priority_for(value: str, fallback: Priority = "ambiguous") -> Priority:
    if _OPTIONAL.search(value):
        return "optional"
    preferred = _PREFERRED.search(value)
    required = _REQUIRED.search(value)
    if preferred and required:
        return "ambiguous"
    if preferred:
        return "preferred"
    if required:
        return "mandatory"
    return fallback


def skill_groups(value: str) -> list[tuple[str, ...]]:
    matches = find_skills(value)
    groups: list[list[str]] = []
    connectors: list[str] = []
    previous = None
    for mention in matches:
        separator = value[previous.end:mention.start] if previous else ""
        if previous and (_ALT.fullmatch(separator) or _COMMA.fullmatch(separator)):
            groups[-1].append(mention.skill.id)
            connectors[-1] += "o" if _ALT.fullmatch(separator) else ","
        else:
            groups.append([mention.skill.id])
            connectors.append("")
        previous = mention
    result = []
    for group, connection in zip(groups, connectors):
        if "o" not in connection:
            result.extend((skill,) for skill in group)
        else:
            result.append(tuple(dict.fromkeys(group)))
    return result


def extract_requirements(description: str, title: str = "") -> Extraction:
    found = []
    seen = set()
    fallback: Priority = "ambiguous"
    responsibilities = False
    for match in _CLAUSE.finditer(description):
        raw = match.group()
        text = normalize(raw).strip(" -•\t")
        heading, colon, remainder = text.partition(":")
        clause_priority = fallback
        if colon and len(heading) < 50:
            if _RESPONSIBILITIES.fullmatch(heading):
                responsibilities, fallback = True, "ambiguous"
                clause_priority = fallback
                text = remainder.strip()
            else:
                inferred = priority_for(heading)
                if inferred != "ambiguous":
                    responsibilities, clause_priority = False, inferred
                    text = remainder.strip()
                    if not text:
                        fallback = inferred
        elif _RESPONSIBILITIES.fullmatch(heading.strip(".")):
            responsibilities, fallback = True, "ambiguous"
            continue
        elif len(text) < 50 and not find_skills(text) and priority_for(text) != "ambiguous":
            responsibilities, fallback = False, priority_for(text)
            continue
        if not text or _NEGATED.search(text):
            continue
        priority = priority_for(text, clause_priority)
        evidence = raw.strip()
        start = match.start() + len(raw) - len(raw.lstrip())
        end = start + len(evidence)
        if responsibilities:
            found.append(Requirement("responsibility", priority, (), evidence, start, end))
            continue
        for group in skill_groups(text):
            identity = (priority, frozenset(group))
            if identity not in seen:
                seen.add(identity)
                found.append(Requirement("skill", priority, group, evidence, start, end))
        if years := _YEARS.search(text):
            found.append(Requirement("experience", priority, (), evidence, start, end, min(50, int(years[1]))))
        if _EDUCATION.search(text):
            found.append(Requirement("education", priority, (), evidence, start, end))
        if _CERTIFICATION.search(text):
            found.append(Requirement("certification", priority, (), evidence, start, end))
        if len(found) >= 200:
            break
    seniority_match = re.search(r"\b(intern(?:ship)?|junior|entry[- ]level|senior|staff|principal|lead)\b", title, re.I)
    role_match = re.search(r"\b(front[- ]?end|back[- ]?end|full[- ]?stack|data|security|devops|research|design)\b", title, re.I)
    requirements = tuple(found[:200])
    skill_ids = {skill for requirement in requirements for skill in requirement.alternatives}
    return Extraction(EXTRACTION_VERSION, TAXONOMY_VERSION,
                      seniority_match[1].casefold() if seniority_match else None,
                      role_match[1].casefold() if role_match else None, requirements,
                      {skill.id: skill.name for skill in SKILLS if skill.id in skill_ids})
