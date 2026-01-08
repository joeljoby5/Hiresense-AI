# Canonical resume document v1

The canonical `ResumeDocument` is a Pydantic value model in `backend/app/domain/resume/`, independent of FastAPI, SQLAlchemy, rendering and AI. Empty documents are valid drafts. Completeness requirements for export or ATS are future workflow rules. Unknown fields are rejected at every model level, avoiding silent loss of unsupported content. The only supported `schema_version` is integer 1; future versions fail explicitly.

## Structure and identities

| Field | Representation |
| --- | --- |
| schema_version, language | Version 1 and a bounded language tag (default en) |
| personal_information | Optional name, headline, email, international free-form phone, location and typed HTTP(S) links |
| professional_summary, career_objective | Separate optional plain-text sections; callers choose which to populate |
| experience | Organization, position, employment type, location, partial dates, ongoing flag, description, bullets and technologies |
| education | Institution, degree, field, location, partial dates, optional expected graduation, academic score, coursework, description and bullets |
| skills | Original spelling/case, optional category/canonical identifier, typed entry-reference evidence |
| projects | Name, description, contribution bullets, achievement bullets, technologies, dates, ongoing flag, status and links |
| certifications | Name, issuer, issue/expiration dates, credential identifier and HTTP(S) URL |
| achievements | Title, description, organization and optional date |
| publications, research, volunteer_experience, leadership_experience | Lists of typed AdditionalEntry values |
| languages | Name and optional descriptive proficiency |
| relevant_coursework | Typed coursework entries |
| custom_sections | UUID section, editable title, description and structured AdditionalEntry values |
| section_order, section_configuration | Stable references, visibility and heading overrides |
| presentation_settings | Separate bounded layout preferences; no rendering implementation |

Major sections have dedicated models. AdditionalEntry deliberately shares title, organization, description, partial dates, ongoing flag, bullets and links across less specialized sections. It avoids identical classes and unvalidated arbitrary dictionaries. Future specialized fields require deliberate schema evolution, not a database table for each section. Technologies are scalar tags owned by their entry; evidence is metadata owned by its skill. They do not carry separate editable entry identities.

Every list entry, bullet, link, coursework item and custom section gets a UUID once, at creation. IDs survive JSON round trips, and duplicates are rejected across the entire document, including nested lists. Skill evidence references an existing entry UUID. Built-in sections use their field names as stable IDs; custom sections use their UUID string. Personal information and single text sections are addressed through those built-in IDs rather than array positions.

## Validation

Task 003 adds an outer maximum of 200 items to every canonical collection, including nested lists, and 10,000 characters to all canonical strings in addition to existing narrower field constraints. The HTTP layer also rejects bodies over 1 MiB before JSON parsing. These are validation bounds, not a JSON/schema migration; prior oversized stored documents fail reconstruction safely and require explicit correction. Existing content is never silently truncated or rewritten.

PartialDate stores an explicit year and optional month, never an invented day/month. Years are integers 1-9999 and months 1-12. A range fails only when it is provably reversed: the earliest possible start must not follow the latest possible end. Same-year ranges with missing month remain valid. Ongoing entries cannot have actual end dates. Education may have expected graduation while ongoing, but cannot simultaneously have actual end and expected graduation. Certification issue/expiry dates use the same ordering rule.

AcademicScore stores value, system and optional scale as separate strings: GPA, CGPA, percentages and descriptive grades are not converted. Empty skill names fail; spelling and case are retained, with outer whitespace trimmed consistently. Email validation uses email-validator through Pydantic, without deliverability/network checks. URLs accept HTTP(S) only. Phone validation is length bounded, without country-specific formatting assumptions.

Text is bounded and HTML tags are rejected; arbitrary HTML/JavaScript objects and embeds have no schema field. This is a plain-text model, not an HTML sanitization engine. Future renderers must escape text and safely encode links; they must never insert user content with raw HTML. User assertions and metrics remain user input, with no generated claims.

Lists/default nested objects are independently allocated. Assignment validation helps local edits; in-place list mutation can bypass immediate validation. Always pass the complete document through `serialize_document` before storing it. It revalidates a JSON-form dump, including mutations made after model construction. Editing callers should prefer constructing a fresh validated document over mutating shared model instances.

## Section and presentation behavior

Section ordering and configuration must reference built-in section names or current custom section UUIDs. Duplicate or unknown references fail. `ordered_section_ids()` appends omitted built-ins in canonical order, followed by omitted custom sections in document order. Thus newly available sections have deterministic placement. Unconfigured sections are visible and retain their standard heading/custom title; explicit configuration overrides that default. Hidden sections retain content for future editing/export choices.

Presentation defaults: default template ID, A4, Arial 11pt, 1.15 line spacing, 8pt section spacing, 20mm margins and #243B53 accent. Letter is supported. Font names are an allowlist with no downloads, font size 8-24pt, spacing bounded, margins 5-50mm and accent a six-digit hex color. All numeric settings reject NaN/infinity. These are metadata only; templates and renderers are not implemented.

## Serialization and evolution

`serialize_document` returns JSON-compatible primitives via `model_dump(mode="json")`; `deserialize_document` validates stored data into a fresh document. UUIDs are strings, partial dates are year/month objects, URLs serialize consistently, and Unicode survives SQLite JSON round trips. UUID fields are preserved, never regenerated when present. Both drafts and snapshots use the same conversion functions. Relational timestamps, ownership and draft revisions are outside this JSON.

A schema change must introduce explicit version dispatch and pure document-to-document conversion from supported older versions, with fixtures proving content and identifier preservation. Keep original snapshots available and define whether older versions are upgraded only in memory or through a separately authorized migration. Unknown future fields/versions must fail rather than be discarded. No conversion framework exists for hypothetical v2 data.
