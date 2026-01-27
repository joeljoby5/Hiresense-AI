# Deterministic ATS methodology

Algorithm `ats-structured-1`, configuration `weights-1`, lexical scorer `pair-tfidf-1`, extraction `job-requirements-1` and taxonomy `technology-2026.1`. No model service is needed.

The taxonomy distinguishes exact aliases from related skills. The matcher chooses longer alternatives first, uses technical token boundaries, and applies limited context rules to short aliases. For example, JavaScript differs from Java, React Native differs from React, and Postgres maps to PostgreSQL. Requirements preserve their source spans in the original description. Supported priority headings and qualification phrases distinguish mandatory, preferred, optional and ambiguous findings. An OR group is satisfied by one documented alternative. The analyzer only scores recognized technical and professional evidence. It keeps unsupported experience duration and credential equivalence unknown.

| Dimension | Weights |
| --- | --- |
| Readability | Text extractability 25, headings 20, logical order 15, contact accessibility 15, layout 15, dates 10 |
| Compatibility | Required skills 30, lexical relevance 25, work/project evidence 20, keyword alignment 15, other qualifications 10 |

Each evaluated component returns a percentage. The displayed percentage is the sum of score × weight divided by the sum of evaluated weights. Coverage is the sum of evaluated weights out of 100. Readability needs at least 50% coverage and is always provisional from structured content. Compatibility needs 75% coverage, and any missing component keeps the score provisional. Extraction and logical reading order are unknown until a real document can be checked. Contact uses presence flags and does not affect compatibility.

Lexical relevance uses smoothed TF-IDF over the exact resume/job pair, `idf = 1 + ln(3 / (1 + df))`, and normalized cosine similarity. Each skill term contributes at most three occurrences with sublinear term frequency. The term projection uses taxonomy identifiers from professional sections and formal job requirement groups. Personal information and dates are excluded from compatibility. Evidence includes canonical section and entry identifiers. Missing evidence means the application could not corroborate a skill from the resume. The scores describe the app's experimental methodology.

`POST /api/v1/analyses` captures an owned current resume draft or checkpoint and an owned job revision in one read transaction. It evaluates outside the transaction and then checks both resources before inserting the immutable report. `GET /api/v1/analyses` lists the latest 20 metadata records for the owner and `GET /api/v1/analyses/{id}` returns the report. Stored inputs preserve evaluated requirements and the canonical resume with direct personal fields replaced by contact-presence flags. Deleting a source resume or job deletes linked analyses. Analysis JSON is capped at 2 MiB per record.

Synthetic tests cover ambiguous boundaries, alternatives, empty vocabularies, repetition, coverage, ownership and immutable inputs. This baseline has no curated gold dataset, equivalence model, verified PDF readability score, or employer outcome calibration. Negation, novel skills, multilingual text and complex alternatives can exceed the extractor's current heuristics.
