# HireSense AI

**Build Smarter. Apply Better. Grow Faster.**

HireSense AI — AI-Powered Resume Builder, ATS Optimization and Career Intelligence Platform.

The long-term goal is to help professionals create resumes, understand job descriptions, evaluate ATS compatibility and make informed career decisions. **Task 003 implements resume application services and REST APIs** on the React/FastAPI and canonical SQLite foundations: owner-scoped CRUD, independent copies, revision conflicts and explicit checkpoints. Development identity is disabled by default. Authentication, the editor, exports, ATS and AI remain deferred. This is a local development application.

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

`GET /api/v1/health` remains application liveness. `GET /api/v1/ready` returns 200 with `{"status":"ready"}` only after database connectivity, required tables/columns and the initial Alembic revision are verified; otherwise it returns a generic 503. It performs synchronous work in FastAPI's worker thread. Readiness may create an empty SQLite file if the parent directory exists, but never creates schema.

Tests run migrations against temporary file databases, including downgrade/re-upgrade and two-connection concurrent operations. They never downgrade the development database:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_persistence.py -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_resume_domain.py -c backend/pytest.ini
```

See [canonical schema](docs/architecture/canonical-resume.md), [persistence and ER diagram](docs/architecture/persistence.md), [decisions](docs/architecture/decisions/002-resume-persistence.md), and the [Task 002 report](docs/development/task-002-report.md).

## Local development identity and resume API

Task 003 reuses migration `0001_resume_foundation`; no new migration is required. Initialize the database as above, then run from the repository root in PowerShell:

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

Direct invocation of the virtual environment's Python avoids PowerShell activation restrictions. Do not change global execution policies. Stop development servers with Ctrl+C.

Ports are strict; occupied ports produce an error rather than silently moving the frontend. Do not terminate unrelated processes. For alternatives, run the backend with `--port 8001`, set `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env`, and use `npm.cmd run dev -- --port 5174`. If using a direct cross-origin backend URL, update `HIRESENSE_ALLOWED_ORIGINS` to the actual frontend origin.

## Verify

From the root:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pip check
Set-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

If Windows denies pytest temporary-directory access, run in a terminal allowed to manage temporary files. A workspace alternative is `--basetemp backend/.local/pytest-task003 -p no:cacheprovider`; use a dedicated disposable directory because pytest clears its base directory. The implementation environment required a scoped run outside its sandbox.

`npm.cmd run preview` serves the production build on loopback port 4173; the development API proxy is intentionally unavailable there. A future deployment needs a same-origin `/api` reverse proxy or a configured absolute API URL and explicit backend CORS origins.

The connection check runs on mount and on retry, not continuously. Stop the backend and press **Check again** to verify the unavailable state, restart it and press **Retry connection** to reconnect. No version is shown until a valid response is received. Requests time out after five seconds; HTTP/network failures and invalid JSON/contracts have separate feedback. This health check confirms only that the API responds, not database or AI availability.

## Repository and architecture

```text
frontend/                 React presentation and API client
  src/app/                Root composition
  src/components/         Connection state presentation
  src/pages/              Foundation screen
  src/services/           Health request and response validation
  src/styles/             Global styling and Tailwind design tokens
backend/
  app/api/                Versioned HTTP routes
  app/core/               Centralized settings
  app/schemas/            Explicit request, response and error contracts
  app/services/           Resume workflows and typed application results
  app/main.py             Application factory and initialization
  app/domain/resume/      Canonical Pydantic resume model (schema v1)
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

The project is a modular monolith with separate browser presentation and REST API boundaries. Resume domain, data access and application workflow services are implemented; domain intelligence and AI adapters remain future work. See [architecture](docs/architecture/overview.md), [progress](docs/development/progress.md) and [implementation report](docs/development/task-001-report.md).

## Roadmap and limitations

Next separately authorized milestone: Task 004, the professional frontend design system, application shell, navigation and resume library interface. The structured editor is Task 005. No frontend resume editor, dashboard, ATS, AI, imports, exports or authentication is implemented here.

The application is not suitable for public deployment. Development identity provides one local configured owner without authentication. The database is not encrypted. SQLite serializes writers with a five-second timeout; short service write scopes reserve the writer before reads, and busy failures return a safe 503. Snapshots are immutable through supported application operations, while trusted direct SQL remains outside that boundary. PostgreSQL and browser rendering/accessibility are unverified. No Git commit, push or deployment was performed.
