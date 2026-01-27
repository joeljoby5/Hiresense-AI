# Workspace and documents

The React Router workspace hosts the resume library, editor, job workspace and analyzer. TanStack Query holds server data in memory. The editor keeps a separate local working draft, a 50-change undo stack, and the latest confirmed server revision. A 750 ms debounce schedules revision-protected saves. A conflict preserves the working draft and offers an explicit copy or reload. Browser storage contains only the theme preference.

Pydantic remains the canonical resume validator. The editor renders structured fields from a generated JSON Schema and keeps stable identifiers for nested records. The schema check compares the committed JSON to the Python model. Accessible move buttons provide keyboard reordering. The PDF and Word adapters consume ordered semantic lines from the same canonical document used by the editor. The preview estimates page count from a continuous browser document. PDF and DOCX paginate through their respective rendering engines.

## Document endpoints

| Method | Path under /api/v1 | Result |
| --- | --- | --- |
| POST | `/resumes/{resume_id}/exports` | Generate an export from `expected_revision` or `version_id` |
| GET | `/resumes/{resume_id}/exports` | List retained metadata |
| GET | `/resumes/{resume_id}/exports/{export_id}` | Return the exact stored attachment |

Exports support PDF, DOCX, TXT and canonical JSON. A short read scope captures the exact source and checks owner/revision. Rendering happens outside the database transaction. The save scope checks owner and source existence again. SQLite retains the 20 most recent exports per owner, each capped at 2 MiB, and cascades deletion from the resume. Download names use only a revision number and validated extension. Responses use attachment and no-store headers. The renderer writes to memory and caps concurrent rendering at one task per process.

ReportLab generates selectable text with embedded Bitstream Vera fonts. Characters outside the embedded font coverage cause a safe validation response. DOCX uses editable headings, lists, links and the selected font family. Extraction tests compare important visible content against the source. JSON preserves the full canonical draft, including hidden sections. PDF/DOCX/TXT follow visibility. ReportLab is BSD and python-docx is MIT. [ReportLab licensing and font embedding](https://docs.reportlab.com/developerfaqs/) · [python-docx package](https://pypi.org/project/python-docx/)

## Job endpoints

`/jobs` supports listing, literal title/company search, sorting and creation. `/jobs/{id}` supports reads, revision-protected replacement, archiving/restoration and deletion. URL validation accepts HTTP(S) links. The application stores those links as data and performs no external fetch. Analysis records retain the exact extracted requirements evaluated at creation. `/jobs/{id}/requirements` returns the current rule-based extraction for review.
