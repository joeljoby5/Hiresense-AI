# HireSense AI

**Build Smarter. Apply Better. Grow Faster.**

HireSense AI — AI-Powered Resume Builder, ATS Optimization and Career Intelligence Platform.

The long-term goal is to help professionals create resumes, understand job descriptions, evaluate ATS compatibility and make informed career decisions. **Task 002 adds the canonical resume model and SQLite persistence foundation** to the working React/FastAPI baseline: validated structured drafts, owner-scoped repositories, revision conflicts, explicit version snapshots and Alembic migrations. Authentication, resume REST workflows, editing, exports, ATS and AI remain deferred.

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

Configuration is optional: sensible development defaults work without `.env` files. To customize:

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
| `HIRESENSE_API_PREFIX` | /api/v1; changing it requires matching `VITE_API_BASE_URL` |
| `HIRESENSE_ALLOWED_ORIGINS` | JSON list of explicit frontend origins |
| `VITE_API_BASE_URL` | /api/v1; may be an absolute backend URL |
| `API_PROXY_TARGET` | http://127.0.0.1:8000; Vite server only |

## Database foundation

The domain document is independent of HTTP and SQLAlchemy. Relational `users`, `resumes` and `resume_versions` tables hold ownership, draft revisions and immutable snapshot metadata; validated JSON stores resume content. Repository operations are internal Python APIs, with no public resume or identity endpoints. A caller-owned transaction commits or rolls back all repository changes together.

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

## Run locally

In PowerShell terminal 1, from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
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
  app/schemas/            Typed response contracts
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

The project is a modular monolith with separate browser presentation and REST API boundaries. The resume domain and data access foundations are implemented; application workflow services, domain intelligence and AI adapters remain future work. See [architecture](docs/architecture/overview.md), [progress](docs/development/progress.md) and [implementation report](docs/development/task-001-report.md).

## Roadmap and limitations

Next separately authorized milestone: Task 003, resume management application services and REST endpoints using the domain and persistence foundation. Subsequent work may add resume editing and versions, document import/export, deterministic ATS analysis, job intelligence, optional provider-independent AI, and career tools.

This foundation has internal ownership records and persistence, with no authentication, public user accounts, resume workflows or AI. PostgreSQL compatibility is architectural intent; no driver or PostgreSQL verification is included. Snapshots are immutable through the repository/ordinary ORM update boundary, not protected against trusted direct SQL. SQLite remains a single-writer database with a five-second busy timeout; callers must keep transactions short. It is intended for local development; production hosting and security hardening are deferred. Windows with 8 GB RAM is the baseline: no large models, Redis, PostgreSQL server, Docker, WSL or background infrastructure are installed. No Git commits, remotes or deployment are part of this task.
