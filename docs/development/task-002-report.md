# Task 002 implementation report

Date: 2026-11-27 (Asia/Calcutta).

## 1. Implementation summary

Implemented the schema-v1 canonical resume domain, SQLAlchemy 2.x/SQLite database infrastructure, reviewed initial Alembic migration, minimal user ownership records, working drafts with optimistic revisions, explicit independent version snapshots and internal repositories. Added separate database readiness without changing liveness. Updated setup, technical architecture, decisions, progress and tests. No Task 003 workflows, public resume endpoints, authentication, frontend features or AI were added.

## 2. Repository inspection and baseline

Read root AGENTS.md, README, architecture overview, progress and Task 001 report; inspected all existing backend configuration/routes/schemas/tests, frontend package/Vite/TypeScript/lint configuration and dependency pins. Git status was clean before implementation; existing code and user processes were preserved. Conventions retained: modular monolith, backend-local Python virtual environment, npm, Pydantic settings with HIRESENSE_ prefix, application factory, exact resolved Python pins and frontend lockfile.

Environment: Windows, Python 3.13.7; existing React 19.3.1, Vite 8.4.0, TypeScript 6.0.3 and Tailwind 4.3.5. Baseline backend: 10 passed in 2.07s, with the preexisting Starlette HTTPX deprecation warning. No baseline failure was hidden or assumed from Task 001. Default development ports were occupied during live verification, so separate task-owned ports 8012/5182 were used.

## 3. Files created

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/0001_resume_foundation_initial_resume_foundation.py`
- `backend/app/api/readiness.py`
- `backend/app/database/__init__.py`
- `backend/app/database/base.py`
- `backend/app/database/session.py`
- `backend/app/domain/__init__.py`
- `backend/app/domain/resume/__init__.py`
- `backend/app/domain/resume/common.py`
- `backend/app/domain/resume/models.py`
- `backend/app/domain/resume/presentation.py`
- `backend/app/domain/resume/sections.py`
- `backend/app/models/__init__.py`
- `backend/app/models/resume.py`
- `backend/app/models/resume_version.py`
- `backend/app/models/user.py`
- `backend/app/repositories/__init__.py`
- `backend/app/repositories/errors.py`
- `backend/app/repositories/resumes.py`
- `backend/app/repositories/users.py`
- `backend/tests/conftest.py`
- `backend/tests/test_persistence.py`
- `backend/tests/test_resume_domain.py`
- `docs/architecture/canonical-resume.md`
- `docs/architecture/decisions/002-resume-persistence.md`
- `docs/architecture/persistence.md`
- `docs/development/task-002-report.md`

## 4. Files modified

- `.gitignore`
- `README.md`
- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/requirements.in`
- `backend/requirements.txt`
- `docs/architecture/overview.md`
- `docs/development/progress.md`

Generated ignored files include the local SQLite database, dependency caches, build output, and `.local/verify-health-task002.mjs`, a port-adjusted copy of the preexisting HTTP/client verification harness. None is a tracked application feature. Small package __init__ files establish actual implemented packages, not empty future architecture layers.

## 5. Dependencies and actual installed versions

| Addition | Actual version | Reason |
| --- | --- | --- |
| SQLAlchemy | 2.0.58 | Typed synchronous ORM, JSON and transaction infrastructure |
| Alembic | 1.20.1 | Explicit schema migrations |
| email-validator | 2.4.0 | Pydantic email validation without ad hoc email parsing |
| greenlet | 3.5.6 | SQLAlchemy transitive |
| Mako | 1.4.3 | Alembic transitive |
| MarkupSafe | 3.0.4 | Mako transitive |
| dnspython | 2.9.2 | email-validator transitive; no deliverability queries are performed |

Installed only these additions into the existing virtual environment. requirements.in records direct intent; requirements.txt pins the full resolved environment. SQLAlchemy intent is constrained to stable 2.0.x. Existing FastAPI 0.165.0, Pydantic 2.14.4, pydantic-settings 2.16.3, Pytest 9.2.0, HTTPX 0.29.0 and other prior pins were unchanged. pip check reports no broken requirements. No global install, ML packages or database server was introduced.

## 6. Canonical resume architecture

The domain is split into common values/date rules, typed section content, presentation/configuration and document aggregation/serialization. It imports neither SQLAlchemy nor FastAPI. It covers every requested root section, including generic typed additional entries for publications/research/volunteering/leadership and UUID custom sections. Empty drafts are valid, while malformed supplied content fails.

Stable UUIDs are generated once for editable entries, nested bullets/links/coursework and custom sections. Whole-document uniqueness, known section references, independent defaults, supported versions, email/HTTP(S) URLs, partial-date chronology, ongoing status, plain text and bounded presentation preferences are validated. Section omission appends remaining sections deterministically; hidden sections preserve their facts. Academic scores retain distinct grading systems. No metrics, achievements or durations are invented. See [canonical schema](../architecture/canonical-resume.md) for precise conventions and constraints.

## 7-8. Tables, relationships and constraints

Implemented tables: users, resumes and resume_versions only, plus Alembic's version table. All entity primary keys use UUIDs. UTCDateTime stores explicit naive UTC in SQL and reconstructs aware UTC at the Python boundary; naive input is rejected.

Users have canonical unique email, nullable password hash, active flag and timestamps. Email normalization validates and strips input, then casefolds the entire address; raw SQL must honor that application convention. Development owners are internal operations restricted to development settings, never auto-seeded or publicly registered. A null hash cannot support future password authentication.

Resumes require an existing owner, valid nonblank title, canonical JSON, positive draft revision and snapshot counter. A composite parent/owner foreign key guarantees same-owner ancestry; a check forbids self-reference. Resume owner/update listing has a composite index. Version uniqueness uses a resume/version-number unique constraint, which also supports resume-prefixed access; redundant indexes are omitted.

User deletion with resumes and parent deletion with children are restricted. Leaf resume deletion cascades snapshots. Canonical JSON shape and longer ancestry-cycle checks are application concerns; no reparent operation exists. The ER diagram and database/application invariant distinction are in [persistence architecture](../architecture/persistence.md).

## 9. Migration configuration

Alembic reads centralized settings and all registered metadata. Config-relative paths work from root or backend/, without machine-specific paths or credentials. SQLite uses batch support and explicit BEGIN for transactional DDL. The initial autogenerated migration was reviewed before applying: custom application datetime references were replaced with frozen SQL DateTime types; constraints, table creation order and reverse downgrade order were retained.

Development initialization explicitly ran upgrade head; no startup create_all exists. Current revision is 0001_resume_foundation. Alembic check found no new upgrade operations from both the test schema and the development database. Only disposable fixture databases were downgraded/re-upgraded.

## 10. Serialization

Both drafts and snapshots use the same revalidated JSON-form Pydantic dump. UUIDs become strings, partial dates retain optional month and Unicode survives persistence. Domain reconstruction validates again and returns independent objects. Unknown fields/versions fail instead of silently disappearing. Updates replace JSON explicitly; no in-place JSON mutation detection is assumed. Future schema evolution must use explicit pure conversions, preserve IDs/content and retain historical originals; no speculative v2 migration framework is installed.

## 11. Sessions and transaction ownership

An engine builder, session factory and context-managed transaction centralize behavior. Repositories execute and flush without commits. The caller commits on success or rolls back on any exception and closes the session. SQLite connections always enforce foreign keys, use a 5000ms busy timeout and support worker-thread use. File databases use normal SQLAlchemy pooling; memory tests use StaticPool. WAL was evaluated and left disabled to avoid persistent journal changes without measured need. Application lifespan disposes its engine. Database work is synchronous; readiness runs through FastAPI's synchronous worker dispatch.

## 12-14. Ownership, revision and snapshot strategies

Every resume and version operation predicates on the trusted owner UUID. Missing and foreign resources share NotFoundError; there is no public identity switching. Future authentication must establish the supplied owner, since this internal boundary is not a login mechanism.

Draft updates use a single owner/ID/expected-revision conditional UPDATE, replace validated content and atomically increment draft_revision. Stale revisions raise RevisionConflictError for a future HTTP 409 mapping. Ordinary edits never create snapshots.

Snapshot creation atomically increments a row counter and captures the returned draft content/revision under that transaction's write lock. Counter allocation and version insert commit/roll back together, with per-resume number uniqueness as a backstop. This avoids MAX()+1 races. Snapshots have independent JSON, source revision and creation time; snapshot creation does not change the draft revision or draft updated_at. No repository update/delete operation exists for versions, and normal ORM historical updates are rejected. Trusted bulk/direct SQL remains outside that guard. Separate-connection concurrency tests prove distinct allocated numbers and rejection of a stale draft write. Busy/locked failures are propagated; whole-transaction retry policy belongs in a later application boundary.

## 15. Commands executed

Inspection: Get-Content of the specified repository/prompt files, rg --files, Get-Location, git status --short, git diff --stat/--name-only/--check, git ls-files, git check-ignore and Get-NetTCPConnection. Development checks used the existing virtualenv Python and npm.cmd.

Dependency installation: `backend/.venv/Scripts/python.exe -m pip install 'SQLAlchemy>=2.0,<2.1' alembic email-validator`, followed by pip freeze to the existing pinned configuration and pip check. The first sandbox install could not access package distribution data; the scoped elevated installation succeeded. No unrelated upgrades occurred.

Migration preparation used Alembic's programmatic revision/autogenerate against an ignored disposable generation database. An initial subprocess path attempt and a temporary-directory permission attempt failed before migration generation; correcting the Windows executable path and using an ordinary ignored directory allowed generation. The migration was then reviewed and frozen before use.

Validation commands:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini --tb=short
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe -m compileall -q backend/app backend/alembic
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini current
# From backend/:
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic check
# From frontend/:
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Live verification used Uvicorn `--host 127.0.0.1 --port 8012`, and Vite with `API_PROXY_TARGET=http://127.0.0.1:8012`, `--port 5182 --bypass-lock` because existing user servers occupied default ports. Ran `node .local/verify-health-task002.mjs live` and Invoke-RestMethod against health/readiness. Both task-owned server sessions were stopped. Existing servers were not stopped. HTTP/client checks do not constitute browser testing.

## 16-18. Actual validation results

| Check | Actual result |
| --- | --- |
| Original baseline | 10 passed, 2.07s |
| Final full backend suite | **63 passed**, 10.86s; 10 existing, 35 domain and 18 persistence cases |
| Warning | One preexisting Starlette HTTPX TestClient deprecation warning; no dependency change made for it |
| Domain | Empty/populated drafts; nested validation; stable/duplicate IDs; future/bool/float versions; partial dates; ongoing rules; invalid email/URLs; presentation; custom/ordered sections; Unicode; round trips; independent defaults; mutated input revalidation |
| Database | Engine, per-connection pragmas, working-directory paths, session cleanup, owner normalization/uniqueness, FK constraints, owner boundaries, JSON validation, title checks, revisions/conflicts, snapshots, immutability guard, cascade/restrict deletion, rollback/counter rollback and naive-timestamp rejection |
| Concurrency | Two writers: one draft success/one conflict; two snapshots: distinct 1/2 numbering |
| Privacy | Bound synthetic private value absent from echo-on/off logs with application DEBUG enabled |
| Migration tests | Fresh temporary upgrade, reflected tables/FKs/indexes/uniqueness, downgrade, re-upgrade and no metadata drift passed |
| Development database | Explicit upgrade/current and backend-directory current/check passed; no development downgrade |
| Readiness | Tests cover initialized, uninitialized, missing table and unavailable path; live initialized database returned 200/ready |
| Health/docs/config/CORS | Existing regression tests and live health/docs/OpenAPI passed |
| Frontend checks | TypeScript and ESLint passed; production build passed (19 modules, 224.20 kB JS / 70.24 kB gzip, 8.03 kB CSS / 2.57 kB gzip) |
| Live client/proxy | Real TypeScript health service -> Vite -> FastAPI passed; frontend HTML/docs/OpenAPI HTTP 200 |
| Dependency/syntax | pip check and compileall passed |
| Git hygiene | Diff whitespace check passed, no tracked databases, database/sidecars ignored, migration source not ignored |
| Server teardown | No listeners remained on task-owned 8012/5182; original development processes preserved |
| Browser UI/accessibility | Unverified, no rendered-browser testing performed |
| PostgreSQL | Unverified; no driver/server installed |

An earlier 52-case sandbox test run had 42 passes and 10 setup errors because Windows blocked pytest temporary directories, not due to assertion failures. Scoped elevated reruns passed; later meaningful privacy/validation/FK/timestamp cases brought the final suite to 63. Initial attempts to launch default-port verification servers failed due to existing processes; alternate loopback ports resolved that without terminating other work. Existing baseline offline/timeout/invalid-response browser-client experiments were not rerun; the frontend service is unchanged and current live connectivity passed.

## 19. Security and privacy

No plaintext password, hardcoded account credential, secret or real professional data was introduced. There is no public development identity, user registration or resume endpoint. All queries use SQLAlchemy bound values; logging hides parameters and suppresses result rows. Readiness never exposes paths, credentials or exception text. Database files, sidecars, journals and local data are ignored, while Alembic source is visible to Git. No destructive reset, commit, push, remote change, history rewrite or deployment was performed.

The initialized local database has schema only, with no seeded owner/resume. File-at-rest encryption and production authorization are not claimed. Access to the workspace/database file is a local operating-system responsibility in this milestone.

## 20. Known limitations

SQLite serializes writes and can raise busy/locked errors after its timeout, especially on read-to-write transaction upgrades; no automatic retry system is added. Domain JSON rules, email normalization and historical immutability rely on trusted repository boundaries; arbitrary direct SQL can bypass them. Longer ancestry cycles are not database-checked; no reparent operation exists. Readiness checks the foundation, not all possible corruption/constraints. Pydantic assignment/list mutation can leave an in-memory object invalid until full revalidation; repository serialization always revalidates it. Plain-text validation is not a future renderer's HTML-escaping implementation.

PostgreSQL, browser visuals/accessibility, production security, authentication, encryption/retention, resume APIs, editor, templates, document parsing/export, ATS and AI are outside this task. Default font choices are preferences, not installed/downloaded font guarantees. The existing upstream HTTPX warning remains.

## 21. Exact manual verification commands

From repository root in PowerShell, using the existing virtual environment:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini current
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini check
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Use another terminal for HTTP verification, with the server running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
Invoke-WebRequest http://127.0.0.1:8000/docs -UseBasicParsing
Invoke-RestMethod http://127.0.0.1:8000/openapi.json
Set-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run dev
```

Use available alternate ports and API_PROXY_TARGET if existing servers occupy defaults; do not terminate unrelated processes. Open http://127.0.0.1:5173 manually to check the foundation screen. Backend tests alone create and downgrade disposable databases; never manually downgrade the real development database as a test. Stop only servers you started with Ctrl+C. No identity bootstrap is needed for readiness.

## 22-23. Handoff

Suggested commit message: `feat: implement canonical resume model and database foundation`.

No commit or push was made. The owner can review all tracked modifications and new source files before committing. Recommended next separately assigned milestone: Task 003 application services and owner-authorized resume management REST endpoints, with explicit DTOs/error mapping and transaction boundaries using this foundation. Do not begin it automatically.
