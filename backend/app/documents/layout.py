from dataclasses import dataclass
from typing import Literal

from app.domain.resume.models import ResumeDocument

Role = Literal["name", "heading", "entry", "text", "bullet", "link"]
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
HEADINGS = {
    "professional_summary": "Professional Summary",
    "career_objective": "Career Objective",
    "volunteer_experience": "Volunteering",
    "leadership_experience": "Leadership",
    "relevant_coursework": "Coursework",
}


@dataclass(frozen=True)
class Line:
    role: Role
    text: str
    url: str | None = None


def join(*values, separator=" · "):
    return separator.join(value for value in values if value)


def date(value):
    if not value:
        return ""
    prefix = MONTHS[value["month"] - 1] + " " if value["month"] else ""
    return prefix + str(value["year"])


def links(values):
    return [Line("link", join(link["label"], link["url"]), link["url"]) for link in values]


def entry_lines(entry):
    title = join(entry.get("position") or entry.get("degree") or entry.get("title") or entry.get("name"),
                 entry.get("field_of_study"))
    organization = join(entry.get("organization") or entry.get("institution") or entry.get("issuer"),
                        entry.get("location"))
    period = join(date(entry.get("start_date")), "Present" if entry.get("ongoing") else date(entry.get("end_date")),
                  separator=" – ")
    score = entry.get("score") or {}
    context = join(period, entry.get("employment_type"), entry.get("proficiency"), entry.get("category"),
                   entry.get("status"), date(entry.get("date")), date(entry.get("issue_date")),
                   "Expires " + date(entry["expiration_date"]) if entry.get("expiration_date") else None,
                   "Expected " + date(entry["expected_graduation"]) if entry.get("expected_graduation") else None,
                   join(score.get("value"), score.get("system"), score.get("scale"), separator=" "),
                   entry.get("credential_id"))
    tags = join(*entry.get("technologies", []), *(item["name"] for item in entry.get("coursework", [])), separator=", ")
    lines = [Line("entry", title), *(Line("text", value) for value in (organization, context, entry.get("description"), tags) if value)]
    lines.extend(Line("bullet", item["text"]) for key in ("contributions", "bullets") for item in entry.get(key, []))
    lines.extend(links(entry.get("links", [])))
    if url := entry.get("credential_url"):
        lines.append(Line("link", url, url))
    return [line for line in lines if line.text]


def document_lines(document: ResumeDocument) -> list[Line]:
    data = document.model_dump(mode="json")
    configs = {item.section_id: item for item in document.section_configuration}
    custom = {item["id"]: item for item in data["custom_sections"]}
    result = []
    for section in document.ordered_section_ids():
        config = configs.get(section)
        if config and not config.visible:
            continue
        if section == "personal_information":
            person = data[section]
            result.extend(line for line in (
                Line("name", person["full_name"]), Line("text", person["headline"]),
                Line("text", join(person["email"], person["phone"], person["location"])),
                *links(person["links"]),
            ) if line.text)
            continue
        value = data.get(section)
        extra = custom.get(section)
        heading = (config.title if config else None) or (extra["title"] if extra else HEADINGS.get(section, section.replace("_", " ").title()))
        if extra:
            body = [Line("text", extra["description"])] if extra["description"] else []
            body.extend(line for item in extra["entries"] for line in entry_lines(item))
        elif isinstance(value, list):
            body = [line for item in value for line in entry_lines(item)]
        else:
            body = [Line("text", value)] if value else []
        if body:
            result.extend([Line("heading", heading), *body])
    return result
