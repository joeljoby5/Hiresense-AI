# HireSense AI

**Build Smarter. Apply Better. Grow Faster.**

HireSense AI — AI-Powered Resume Builder, ATS Optimization and Career Intelligence Platform.

The long-term goal is to help professionals create resumes, understand job descriptions, evaluate ATS compatibility and make informed career decisions. **Task 001 implements only the development foundation:** a React screen, a typed FastAPI health endpoint, real connectivity feedback and project documentation. No resume, database, authentication or AI features are implemented.

## Stack and prerequisites

- Windows PowerShell; Python 3.13 (validated on 3.13.7).
- Node.js 22.12 or newer in the 22 series (validated on 22.16.0), npm (10.9.2 validated), Git.
- React, TypeScript, Vite 8, Tailwind CSS 4; FastAPI, Pydantic settings, Uvicorn; Pytest/HTTPX.
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
| `HIRESENSE_API_PREFIX` | /api/v1; changing it requires matching `VITE_API_BASE_URL` |
| `HIRESENSE_ALLOWED_ORIGINS` | JSON list of explicit frontend origins |
| `VITE_API_BASE_URL` | /api/v1; may be an absolute backend URL |
| `API_PROXY_TARGET` | http://127.0.0.1:8000; Vite server only |

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
  tests/                  API, configuration and CORS tests
  requirements.in         Direct dependency intent
  requirements.txt        Exact resolved runtime/test dependency pins
docs/architecture/        Implemented boundaries and future architecture
docs/development/         Milestone status and actual validation evidence
AGENTS.md                 Durable development instructions
```

The project is a modular monolith with separate browser presentation and REST API boundaries. Application services, domain intelligence, data access and AI adapters will be introduced when their features require them. No empty service layers or database stubs are created. See [architecture](docs/architecture/overview.md), [progress](docs/development/progress.md) and [implementation report](docs/development/task-001-report.md).

## Roadmap and limitations

Next separately authorized milestone: canonical resume domain model, SQLite, SQLAlchemy and Alembic migrations. Subsequent work may add resume editing and versions, document import/export, deterministic ATS analysis, job intelligence, optional provider-independent AI, and career tools.

This foundation has no persistence, user accounts, resume workflows or AI. It is intended for local development; production hosting and security hardening are deferred. Windows with 8 GB RAM is the baseline: no large models, Redis, PostgreSQL server, Docker, WSL or background infrastructure are installed. No Git commits, remotes or deployment are part of this task.
