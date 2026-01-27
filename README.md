# HireSense AI

**Build Smarter. Apply Better. Grow Faster.**

HireSense AI — AI-Powered Resume Builder, ATS Optimization and Career Intelligence Platform.

HireSense currently provides account-based workspaces, a resume library and structured editor, six live preview templates, revision-specific PDF/DOCX/TXT/JSON exports, a job workspace, and a deterministic resume analyzer. The analyzer shows separate readability and job compatibility estimates with source evidence and evaluation coverage. A labeled mock writing assistant works without any AI service. See the [implementation status](docs/development/master-implementation-progress.md).

[Resume analyzer screenshot with synthetic data](docs/images/resume-analyzer.png)

## Stack and prerequisites

- Windows PowerShell; Python 3.13 (validated on 3.13.7).
- Node.js 22.12 or newer in the 22 series (validated on 22.16.0), npm (10.9.2 validated), Git.
- React, TypeScript, Vite 8, Tailwind CSS 4; FastAPI, Pydantic settings, Uvicorn; SQLAlchemy 2.x/Alembic with built-in SQLite; Pytest/HTTPX.
- Internet access for initial dependency installation. No paid keys, GPU, containers or external services required.

Vite's supported runtime range is recorded in `frontend/package.json`. No global dependency installation is needed.

## Setup on Windows

From the repository root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Set-Location frontend
npm.cmd ci
Set-Location ..
```

Health/readiness configuration is optional. Resume operations additionally require explicit local identity setup below. To customize:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Backend settings are loaded from `backend/.env`, independent of the shell's working directory; process environment variables take precedence. Frontend configuration is loaded by Vite from `frontend/.env` and requires restarting Vite after changes. Examples are tracked; actual environment files are ignored. Only `VITE_` values are exposed to the browser: never place secrets there.

| Setting | Default / purpose |
| --- | --- |
| `HIRESENSE_APP_NAME`, `HIRESENSE_APP_VERSION` | HireSense AI, 0.1.0 |
| `HIRESENSE_ENVIRONMENT`, `HIRESENSE_DEBUG` | development, false |
| `HIRESENSE_DATABASE_URL` | SQLite at `backend/.local/data/hiresense.sqlite3`; relative SQLite paths resolve from `backend/` |
| `HIRESENSE_DATABASE_ECHO` | false; optional SQL statement logging with parameters hidden and result rows suppressed |
| `HIRESENSE_DEVELOPMENT_IDENTITY_ENABLED` | false; explicitly opt in for local development only |
| `HIRESENSE_DEVELOPMENT_OWNER_ID` | UUID printed by the explicit owner initialization command |
| `HIRESENSE_API_PREFIX` | /api/v1; changing it requires matching `VITE_API_BASE_URL` |
| `HIRESENSE_ALLOWED_ORIGINS` | JSON list of explicit frontend origins |
| `VITE_API_BASE_URL` | /api/v1; may be an absolute backend URL |
| `API_PROXY_TARGET` | http://127.0.0.1:8000; Vite server only |

## Database foundation

The domain document is independent of HTTP and SQLAlchemy. Relational `users`, `resumes` and `resume_versions` tables hold ownership, draft revisions and immutable snapshot metadata; validated JSON stores resume content. Application services expose owner-scoped resume workflows through typed REST routes. A service-owned transaction commits or rolls back all repository changes together. Identity has no HTTP endpoint.

The default database is **`backend/.local/data/hiresense.sqlite3`**, resolved independently of your shell directory. Local data and SQLite sidecars are ignored by Git. SQLite is a built-in file database; no server installation is needed. Keep real resumes private and backed up appropriately: the local file is not encrypted by this application.

After installing requirements, explicitly initialize or upgrade the database from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini current
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini check
```

Or from `backend/`, use `.venv/Scripts/python.exe -m alembic upgrade head`. Migrations create the configured SQLite parent directory; application startup never creates tables. Change `HIRESENSE_DATABASE_URL` in the backend environment for another database file. Quote absolute Windows SQLite URLs using forward slashes, e.g. `sqlite:///D:/private/hiresense.sqlite3`. Existing default data is not moved when configuration changes. Leave SQL logging disabled except for local debugging.

`GET /api/v1/health` reports application liveness. `GET /api/v1/ready` verifies database connectivity, required schema objects and the current Alembic revision `0005_account_sessions`. It returns 503 until those requirements are met. Apply `upgrade head` to enable the new workspace features in an existing database.

Tests run migrations against temporary file databases, including downgrade/re-upgrade and two-connection concurrent operations. They never downgrade the development database:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_persistence.py -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_resume_domain.py -c backend/pytest.ini
```

See [canonical schema](docs/architecture/canonical-resume.md), [persistence and ER diagram](docs/architecture/persistence.md), [decisions](docs/architecture/decisions/002-resume-persistence.md), and the [Task 002 report](docs/development/task-002-report.md).

## Local development identity and resume API

Regular workspace use starts with registration in the browser. The optional development owner supports API testing without a session. Initialize or upgrade the database as above, then configure the local owner from the repository root in PowerShell if you need that mode.

```powershell
$env:HIRESENSE_ENVIRONMENT='development'
$env:HIRESENSE_DEVELOPMENT_IDENTITY_ENABLED='true'
Set-Location backend
.venv/Scripts/python.exe -m app.initialize_owner
# Copy the UUID printed by the command:
$env:HIRESENSE_DEVELOPMENT_OWNER_ID='<printed UUID>'
Set-Location ..
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --no-access-log
```

The initialization command is explicit and idempotent. It creates/reuses one synthetic internal development owner with no password, and rejects inactive or conflicting configured owners. To persist settings locally, put the same values in ignored `backend/.env`. Process variables are scoped to the current terminal and override that file.

The resolver requires an explicitly enabled development environment, configured active owner and loopback connection. It does not trust Host or owner headers as identity. Missing/disabled/production identity returns 503, and ordinary requests never create accounts. Do not expose Vite, Uvicorn, a proxy or a tunnel publicly: this mode is not authentication. Health and readiness work without identity.

| Endpoint under `/api/v1` | Behavior |
| --- | --- |
| `POST /resumes` | Create title + optional content, 201 with Location |
| `GET /resumes` | Metadata page; limit/offset/search/sort |
| `GET /resumes/{id}` | Validated canonical detail |
| `PATCH /resumes/{id}` | Title and/or complete content replacement, expected_revision required |
| `DELETE /resumes/{id}?expected_revision=R` | Hard delete and cascade checkpoints, empty 204 |
| `POST /resumes/{id}/duplicate` | Optional custom title, independent copy, 201 |
| `POST /resumes/{id}/versions` | Explicit checkpoint at expected_revision, 201 |
| `GET /resumes/{id}/versions` | Paginated checkpoint metadata |
| `GET /resumes/{id}/versions/{version_id}` | Preserved canonical content |

Try the complete lifecycle in `/docs`. New drafts start at revision 1. Title/content updates share one atomic revision and return 409 for stale state; null replacements are rejected. Copies preserve document entry IDs and source lineage, without copying history. Deleting a parent preserves independent children, clears their parent references and advances their revisions. Only the deleted resume's checkpoints cascade.

Lists default to limit 20 (maximum 100), offset 0 (maximum 1,000,000), updated_desc; supported sorts also include updated_asc/title_asc/title_desc with UUID tie breaking. Search is a bounded literal title substring: %, _ and / are escaped; SQLite folds ASCII case only. Bodies are limited to 1 MiB, canonical collections to 200 items each, and existing narrower text limits remain. Oversized previously stored documents may need explicit correction; no data is rewritten.

Errors have stable `error.code`, safe message, server request ID and optional current revision/field categories. No input values or SQL details are returned. Logs use route templates without query/body data; X-Request-ID correlates requests. See [API architecture and examples](docs/architecture/resume-api.md), [ADR 003](docs/architecture/decisions/003-resume-services-api.md) and [Task 003 report](docs/development/task-003-report.md).

For a synthetic manual request in a second terminal:

```powershell
$base='http://127.0.0.1:8000/api/v1'
$resume = Invoke-RestMethod -Method Post -Uri "$base/resumes" -ContentType 'application/json' -Body '{"title":"Synthetic manual draft"}'
Invoke-RestMethod -Uri "$base/resumes/$($resume.id)"
Invoke-RestMethod -Method Patch -Uri "$base/resumes/$($resume.id)" -ContentType 'application/json' -Body '{"expected_revision":1,"title":"Revised synthetic draft"}'
Invoke-RestMethod -Method Post -Uri "$base/resumes/$($resume.id)/versions" -ContentType 'application/json' -Body '{"expected_revision":2,"change_summary":"Manual checkpoint"}'
Invoke-RestMethod -Method Delete -Uri "$base/resumes/$($resume.id)?expected_revision=2"
```

Delete only the synthetic resource created by those commands. For a fully isolated real HTTP lifecycle (including stale revisions, copying, checkpoints and cleanup), use:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/verify_resume_api.py
```

That script migrates a disposable database under ignored backend/.local, bootstraps an owner, starts an owned loopback server on an available port, checks actual HTTP outcomes, stops the server and removes the database. It never uses the ordinary development database. It does not claim browser verification.

## Run locally

In PowerShell terminal 1, from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --no-access-log
```

In terminal 2:

```powershell
Set-Location frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs; schema: http://127.0.0.1:8000/openapi.json; health: http://127.0.0.1:8000/api/v1/health.

Create a local account using **Sign in** and **Create an account**. In **My resumes**, create a draft, open its editor, and wait for **Saved**. Use the history page to create a checkpoint or generate an export. In **Job workspace**, paste a description and review the extracted requirements. In **Resume analyzer**, choose a draft or checkpoint and an active saved job, then inspect the scores, weighted findings and evidence.

Direct invocation of the virtual environment's Python avoids PowerShell activation restrictions. Do not change global execution policies. Stop development servers with Ctrl+C.

Ports are strict; occupied ports produce an error rather than silently moving the frontend. Do not terminate unrelated processes. For alternatives, run the backend with `--port 8001`, set `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env`, and use `npm.cmd run dev -- --port 5174`. If using a direct cross-origin backend URL, update `HIRESENSE_ALLOWED_ORIGINS` to the actual frontend origin.

## Verify

From the root:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe backend/scripts/generate_resume_schema.py --check
backend/.venv/Scripts/python.exe backend/scripts/verify_workspace.py
Set-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

If Windows denies pytest temporary-directory access, run in a terminal allowed to manage temporary files. A workspace alternative is `--basetemp backend/.local/pytest-task003 -p no:cacheprovider`; use a dedicated disposable directory because pytest clears its base directory. The implementation environment required a scoped run outside its sandbox.

`npm.cmd run preview` serves the production build on loopback port 4173; the development API proxy is intentionally unavailable there. A future deployment needs a same-origin `/api` reverse proxy or a configured absolute API URL and explicit backend CORS origins.

The browser harness starts loopback Vite and Uvicorn against a disposable migrated database. It uses installed Microsoft Edge on Windows or Playwright Chromium on other platforms. Close a conflicting port 5184 or use a different test environment.

## Repository and architecture

```text
frontend/                 React presentation and API client
  src/app/                Root composition
  src/features/           Resume library, editor, jobs and analyzer
  src/services/           Shared workspace HTTP client and liveness client
  e2e/                    Synthetic browser workflows
  src/styles/             Global styling and Tailwind design tokens
backend/
  app/api/                Versioned HTTP routes
  app/core/               Centralized settings
  app/schemas/            Explicit request, response and error contracts
  app/services/           Resume, document, job and analysis workflows
  app/main.py             Application factory and initialization
  app/domain/resume/      Canonical Pydantic resume model (schema v1)
  app/domain/intelligence/ Skill taxonomy, extraction, lexical scoring and ATS evidence
  app/documents/          Semantic resume layout and document rendering
  app/database/           Engine, session, transaction and UTC conventions
  app/models/             Relational SQLAlchemy entities
  app/repositories/       Internal owner-scoped operations (no commits)
  alembic/                Reviewed, explicit schema migrations
  tests/                  Domain, database, migration, API and configuration tests
  requirements.in         Direct dependency intent
  requirements.txt        Exact resolved runtime/test dependency pins
docs/architecture/        Implemented boundaries and future architecture
docs/development/         Milestone status and actual validation evidence
AGENTS.md                 Durable development instructions
```

The project is a modular monolith. The browser uses owner-scoped API contracts, and domain scoring and document formatting run independently of the UI. See [architecture](docs/architecture/overview.md), [workspace and document design](docs/architecture/workspace.md), [analysis methodology](docs/architecture/ats.md) and the [master specification](docs/MASTER_SPECIFICATION.md).

## Roadmap and limitations

Regular accounts use password authentication and server-managed sessions. The optional developer identity owns separate local data. Public hosting still requires HTTPS configuration, production hardening and verification. Resume and job data are stored in unencrypted SQLite. The app retains the most recent 20 exports and 20 ATS analyses per owner. Deleting a resume removes its checkpoints, exports and linked analyses. Deleting a job removes its linked analyses. See [account security](docs/architecture/accounts.md).

Set `HIRESENSE_AI_PROVIDER=disabled` to turn off writing assistance. The default `mock` adapter only normalizes whitespace. The `ollama` and `openai-compatible` settings require `HIRESENSE_LOCAL_AI_ORIGIN` with a loopback IP and explicit port, plus `HIRESENSE_LOCAL_AI_MODEL` matching a locally configured model. The application sends only the selected saved summary with explicit consent. The adapters were verified with controlled HTTP responses. A separately installed runtime is needed to verify real inference.

The browser preview uses estimated pagination. PDF font coverage is limited to the embedded Bitstream Vera fonts. Choose DOCX, TXT or JSON for text outside that coverage. ATS results are experimental, coverage-aware estimates. The rule-based extractor can miss qualifications or misread context. See the [progress tracker](docs/development/master-implementation-progress.md) for pending features and the next implementation action.
