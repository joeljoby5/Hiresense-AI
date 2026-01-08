# Development progress

Updated: 2026-11-27 (Asia/Calcutta).

## Current milestone

Task 002: canonical resume domain, SQLite/SQLAlchemy persistence, repositories and Alembic migrations. Implementation and supported checks complete. Scope stops before Task 003.

## Completed foundation

Task 001's React/TypeScript/Vite/Tailwind presentation, FastAPI application factory, settings, explicit CORS, health contract and frontend health client are preserved. Its historical results remain in [Task 001 report](task-001-report.md). The clean baseline was rechecked: 10 existing backend tests passed before changes.

Task 002 adds typed schema-v1 resume content with stable UUIDs, partial dates, extended/custom sections, section visibility/order and bounded presentation metadata. Internal repositories persist revalidated JSON with owner-aware access, atomic expected-revision updates and explicitly created independent snapshots. SQLAlchemy manages three relational entities, UTC timestamps, foreign keys and caller-owned transactions. Alembic initialization is explicit; startup never creates tables. Readiness is separate from existing liveness.

## Actual validation

| Check | Result |
| --- | --- |
| Baseline backend | 10 passed, one existing Starlette/HTTPX deprecation warning |
| Final backend | **63 passed**, 10.86s; 35 domain, 18 persistence/migration/readiness, 10 original regression cases |
| Concurrency | Two separate SQLite connections: one stale revision rejected; snapshot numbers 1 and 2 allocated distinctly |
| Migrations | Fresh temporary upgrade, inspected constraints/indexes, downgrade, re-upgrade and metadata comparison passed |
| Development database | Explicit upgrade to 0001_resume_foundation; current/check work from repository root and backend/; no drift |
| Readiness | Automated 200/503 states, missing schema and unavailable file; live initialized database returned ready/200 |
| Logging privacy | Echo on/off with inherited DEBUG: synthetic private value absent from captured logs |
| Dependency consistency | pip check passed; unrelated packages unchanged |
| Frontend | TypeScript, ESLint and production build passed; no frontend source/configuration edits |
| Live integration | Actual frontend TypeScript health client through Vite proxy to Uvicorn passed; HTML/docs/OpenAPI HTTP 200 |
| Git ignores | Database, WAL/SHM and journal files ignored; migration source visible; no tracked databases |
| Syntax/whitespace | compileall and git diff --check passed |
| Temporary servers | Task-owned ports 8012/5182 stopped; existing 8000/5173 processes left running |
| Browser UI / PostgreSQL | Unverified; no browser or PostgreSQL tests performed |

Default SQLite database: `backend/.local/data/hiresense.sqlite3`, ignored and initialized without personal data or development owner seeding. Disposable test databases alone were downgraded. Sandbox installation/temporary-directory restrictions required scoped elevated execution; ordinary project commands are documented in README.

## Limitations and handoff

One existing upstream Starlette HTTPX deprecation warning remains. No authentication, public resume APIs, editor, rendering, ATS or AI functionality is implemented. Snapshot immutability is an application/ordinary ORM boundary; trusted SQL can bypass it. SQLite remains a single-writer database; short transactions and future safe whole-transaction retries may be needed under load. The application does not encrypt the database file. Browser rendering/accessibility and PostgreSQL remain unverified.

See [Task 002 report](task-002-report.md), [canonical schema](../architecture/canonical-resume.md), [persistence](../architecture/persistence.md) and [ADR 002](../architecture/decisions/002-resume-persistence.md). Next separately assigned milestone: Task 003, resume management application services and REST endpoints. No commit, push or deployment was performed.
