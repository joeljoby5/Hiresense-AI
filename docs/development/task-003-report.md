# Task 003 implementation report

Date: 2026-11-27 (Asia/Calcutta).

## 1. Implementation summary

Implemented resume application services and REST APIs for create, retrieve, list/search/sort, title/content replacement, revision-protected deletion, independent duplication and explicit checkpoints. Added controlled development identity, safe errors/logging, request bounds, tests and documentation. Existing frontend source is unchanged. Scope stops before Task 004.

## 2. Repository inspection

Read AGENTS.md, README, Task 001/002 reports, progress, architecture/canonical/persistence documentation and ADR 002. Inspected domain, ORM, repository, session, settings, routes, automated tests and Alembic configuration. Initial Git status was clean. Existing virtualenv/npm dependencies were reused.

Task 002 was present: three entities, canonical schema v1, owner-aware repositories, caller-owned transactions, initial revision 1, conditional draft writes and transactional snapshot counters. Current development migration was `0001_resume_foundation (head)`. Existing version lookup used a number; the public UUID route adds an owner/resume-scoped UUID lookup while preserving the older method.

The schema supports all requested workflows without migration. The main policy extension resolves Task 002's deferred parent-deletion handling: direct children are detached transactionally and preserved, with a new revision. Raw SQL parent deletion remains RESTRICTed.

## 3. Initial baseline results

First sandbox run: 45 passed, 18 setup errors from denied pytest Windows temporary-directory access, plus cache warnings. A workspace temporary directory encountered the same sandbox restriction. Scoped execution outside the sandbox with a dedicated disposable base passed: **63 tests, one existing Starlette/HTTPX warning, 1.99s**. No assertions were weakened or tests skipped.

## 4. Files created

- `backend/app/api/errors.py`, `identity.py`, `resumes.py`: centralized error/identity adapters and thin typed routes.
- `backend/app/core/request_context.py`: streaming-body bounds, correlation and safe logging.
- `backend/app/database/resume_scope.py`: active-owner check and transaction adapter.
- `backend/app/initialize_owner.py`: explicit idempotent development CLI bootstrap.
- `backend/app/repositories/interfaces.py`: structural repository and record interfaces without ORM imports.
- `backend/app/schemas/errors.py`, `resumes.py`: strict request/list models, documented error contracts and reused typed application responses.
- `backend/app/services/__init__.py`, `errors.py`, `resumes.py`: application workflows/results.
- `backend/scripts/verify_resume_api.py`: isolated real HTTP lifecycle and owned-server cleanup.
- `backend/tests/test_resume_services.py`, `test_resume_api.py`: workflow, concurrency, rollback, ownership, identity and API cases.
- `docs/architecture/resume-api.md`, `decisions/003-resume-services-api.md`, this report.

## 5. Files modified

- `backend/.env.example`, `app/core/config.py`: identity settings, default off.
- `backend/app/main.py`: composition, routes, error handlers, middleware, mutation CORS and safe logging.
- `backend/app/database/session.py`: opt-in SQLite BEGIN IMMEDIATE for service writes.
- `backend/app/repositories/resumes.py`, `errors.py`: shared state revisions, metadata pages, deletion, conditional checkpoints, UUID version lookup and safe revision metadata.
- `backend/app/domain/resume/common.py`, `tests/test_resume_domain.py`: targeted collection/string bounds and regression tests.
- `backend/app/api/health.py`, `readiness.py`: System documentation tag; existing response contracts preserved.
- `README.md`, architecture overview/persistence/canonical docs and development progress: current setup, behavior, limits and evidence.

## 6. Dependencies

None added or upgraded. Reused FastAPI/Pydantic, synchronous SQLAlchemy, Alembic, Pytest/HTTPX, built-in SQLite and standard library. No infrastructure, ML, AI or frontend package changes. pip check reports no broken requirements.

## 7. Application architecture

Routes validate/serialize HTTP and call ResumeService. Services coordinate existing repositories through a focused structural ResumeStore interface and injected transaction scope. Services import neither HTTP nor SQLAlchemy. Typed application results expose only supported public fields and are reused by response schemas. The canonical domain model is reused; no second implementation, duplicate domain or generic service framework was introduced. See [API architecture](../architecture/resume-api.md) and [ADR 003](../architecture/decisions/003-resume-services-api.md).

## 8. REST endpoints

All under the existing configurable prefix, default `/api/v1`:

| Method | Path | Success |
| --- | --- | --- |
| POST | `/resumes` | 201 + Location |
| GET | `/resumes` | 200 metadata page |
| GET | `/resumes/{resume_id}` | 200 detail |
| PATCH | `/resumes/{resume_id}` | 200 updated detail |
| DELETE | `/resumes/{resume_id}?expected_revision=R` | 204, empty |
| POST | `/resumes/{resume_id}/duplicate` | 201 + Location |
| POST | `/resumes/{resume_id}/versions` | 201 + Location |
| GET | `/resumes/{resume_id}/versions` | 200 metadata page |
| GET | `/resumes/{resume_id}/versions/{version_id}` | 200 preserved content |

Health/readiness contracts remain unchanged. Swagger exposes typed inputs/results, summaries, error responses and System/Resumes/Resume versions tags.

## 9. Request and response schemas

Strict create/update/duplicate/checkpoint/list request models reject unexpected fields. JSON revision inputs are strict positive integers; services independently check their business preconditions. PATCH omission preserves fields, explicit null is invalid, and supplied content replaces the complete document. Empty updates fail.

Resume detail exposes UUID, title, validated canonical content, revision, nullable parent and UTC timestamps. Lists omit documents and owners. Version metadata exposes UUID/number/source revision/schema version/summary/time; detail adds preserved canonical content. Entry IDs, Unicode and partial dates survive serialization. ORM entities are never unrestricted API responses.

Pages expose items/total/limit/offset/has_more. Limit defaults to 20, max 100; offset 0 through 1,000,000. Resume sorts: updated_desc/default, updated_asc, title_asc, title_desc, all with ascending UUID ties. Versions sort by descending number. Metadata-only queries avoid loading documents. Search is a trimmed max-200 title substring, with bound parameters and literal %, _ and / escaping. SQLite folds ASCII case only; title sorting uses its default collation.

## 10. Development identity

Default off. Requires exactly environment development, explicit enabled flag, configured UUID, loopback ASGI peer, and an existing active User. HTTP Host alone, forwarded/owner headers and request owner fields do not establish identity. Disabled/production/missing/inactive/remote contexts fail closed with 503; health/readiness do not require identity.

Explicit `python -m app.initialize_owner` creates/reuses synthetic `local-developer@example.org` without a password and prints its UUID configuration. It requires enabled development mode, is idempotent and rejects conflicting configured or inactive owners. HTTP requests never create accounts. No owner was seeded in the ordinary database during implementation. Tests/bootstrap verification used isolated databases only.

This is not login or public authentication. Run both servers on loopback; a public proxy/tunnel can forward loopback traffic and would defeat the local-use assumptions.

## 11. Ownership enforcement

Each service operation uses the trusted internal owner and verifies active ownership within its transaction. Repository predicates retain owner/resource boundaries. Foreign and unknown resumes share the same 404/code. Version lookup enforces owner, resume and version association. Payload owner/protected-field overrides fail validation and listings exclude other owners.

## 12. Transactions

One application scope commits or rolls back the whole operation and closes sessions. Repositories only execute/flush. Result reconstruction/validation occurs before commit. Tests inject failures after actual writes to verify duplicate rollback, checkpoint insert/counter rollback, parent deletion/child detachment rollback and API integrity-failure rollback.

SQLite service writes reserve the writer with BEGIN IMMEDIATE before owner/source reads, avoiding read-to-write upgrade failures. Existing plain transactions/read scopes retain BEGIN; atomic conditional predicates still protect revisions. The engine/session factory is shared per application, foreign keys/timeouts remain enabled, and lifespan disposes the engine. No retries, async DB framework or external work inside transactions was added.

## 13. Revision behavior

New drafts retain initial revision 1. PATCH advances exactly once for title/content/both; even equal replacement values count as a successful update. Stale requests return 409/current_revision/request_id and never overwrite. DELETE requires an expected revision. Services independently reject absent, boolean, non-integer or nonpositive revisions. Tests cover simultaneous separate-connection service writers and two HTTP clients reading the same revision.

## 14. Duplication

New resume UUID, revision 1, independent validated content, source parent reference and no copied history. Document-scoped entry IDs/facts remain intact. Default titles truncate to fit ` (copy)` within 200 characters; custom titles use ordinary validation. Editing copies leaves originals/checkpoints unchanged. No job tailoring or AI exists.

## 15. Deletion

Hard deletion checks/reserves expected parent revision, clears direct child lineage and advances each child's revision/timestamp, then deletes the target and its cascading checkpoints. Children, their checkpoints, grandchildren and unrelated owners' resumes survive. A failure anywhere rolls back all steps. Existing composite foreign keys and raw parent-delete RESTRICT remain unchanged. No soft-delete infrastructure or schema change.

## 16. Snapshots

Reuse the existing transactional row counter and uniqueness constraint. Expected revision is included in the allocation UPDATE, which captures exact draft JSON/revision under its write lock. Insert/allocation roll back together; failed or stale creation consumes no committed number. Snapshots do not change draft revision/updated_at. Reads revalidate content; normal edits never create history. No restore, version deletion, diff or automatic snapshots.

## 17. Errors

Typed envelope contains code, safe message, request_id, optional current_revision and bounded field categories. Codes/statuses cover not-found 404, revision conflict 409, oversized body 413, invalid request/content 422, unavailable identity/database 503 and internal/integrity error 500. Framework HTTP exceptions retain status with generic messages. Readiness retains its preexisting 503 body.

Validation details omit input/ctx/exception strings, redact unknown field names and cap details at 50. Corrupt persisted JSON is a safe internal error. Operational database failures return generic 503; unexpected integrity failures deliberately return 500 and roll back. Debug logging never enables HTTP tracebacks.

## 18. Logging and privacy

Server-generated X-Request-ID values ignore incoming IDs and match error bodies. Logs contain method, route template, status, duration, request ID and safe success/error category. No bodies, query strings, concrete resource paths, personal content or exception text are logged by the request infrastructure. Raw Uvicorn access logging is disabled; startup commands also specify --no-access-log. SQL parameter/result suppression is preserved.

Bodies are capped at 1 MiB before JSON parsing, including streamed bodies with false/missing Content-Length. Canonical lists, including nested lists, are capped at 200 items. Strings have an outer 10,000-character limit plus narrower existing field constraints. This intentional validation tightening has regression tests; oversized previously persisted JSON now fails reconstruction safely and needs explicit correction. Stored content is never truncated or rewritten.

## 19. Migrations

No migration added/modified. Current remains 0001_resume_foundation. Alembic check against the existing development schema reports no new upgrade operations. Temporary fixture tests verify fresh upgrade, reflected constraints, downgrade/re-upgrade and metadata compatibility. No genuine database downgrade/reset was performed.

## 20. Actual automated results

| Check | Result |
| --- | --- |
| Baseline | 63 passed, one existing warning, 1.99s after sandbox workaround |
| Final full backend suite | **139 passed**, 9.44s, one existing Starlette/HTTPX warning |
| Existing regressions | All 63 preserved and passing |
| New/expanded coverage | 76 additional service/API/security/resource-bound cases |
| Dependency check | pip check passed |
| Syntax | compileall app/scripts passed |
| Migration drift | alembic check passed, no new operations |
| Whitespace | git diff --check passed; non-blocking LF/CRLF normalization notice |

Inspected installed Starlette TestClient source: it explicitly supports the installed httpx fallback and emits the recommendation to install httpx2. Execution succeeds. No unrelated dependency upgrade was made to silence the warning. Intermediate 128- and 130-case suites also passed before final bounds/precondition additions.

## 21. Real HTTP verification

The checked-in script created a disposable migrated database, initialized the controlled owner and started a real Uvicorn process on an available loopback port. Expected outcomes passed: health/readiness/docs/schema 200; create 201; canonical retrieval 200; title edit 200/revision 2; stale update 409/current revision 2; checkpoint 201; independent duplicate 201 and copy update 200; unchanged original/checkpoint; version/list 200; deletion 204 with empty body; deleted lookup 404; surviving detached copy at revision 3; unchanged sentinel resume; final synthetic cleanup and empty list.

First lifecycle passed HTTP checks but Windows held a transient bootstrap/migration sqlite3 handle during directory cleanup. Explicit garbage collection in the harness released those cycles. Rerun passed HTTP checks, owned-server stop and actual directory removal, exit code 0. The first leftover task-created directory was separately verified by resolved absolute path and removed. No genuine resumes were modified or deleted.

## 22. Frontend regression

TypeScript passed, ESLint passed with zero warnings, production build passed: 19 modules, JS 224.20 kB / gzip 70.24 kB, CSS 8.03 kB / gzip 2.57 kB. No frontend source/config/dependency modifications.

The real frontend TypeScript fetchHealth client was transpiled/executed in a Node harness through Vite 5183 to Uvicorn 8013. Correct health data, frontend HTML, API docs and schema all passed. Both task-owned processes were stopped; socket checks found no listeners on 8013/5183. No unrelated processes were stopped. This is HTTP/client verification, not rendered browser testing.

## 23. Security verification

Cross-owner retrieve/update/delete/duplicate/checkpoint/version-list/version-detail return indistinguishable missing-resource responses. Listings exclude foreign resumes. Protected-field injection is rejected; owner headers cannot select another owner. Resolver covers disabled, production, missing configuration, missing/inactive user, remote peer and allowed loopback. Version association, invalid UUIDs, null semantics, strict revisions, literal SQL wildcard search, invalid JSON, nested/streamed size limits, error/log privacy, request IDs, CORS and OpenAPI response schemas are tested.

## 24. Limitations and unverified checks

No public authentication/deployment, encryption, retention/export workflow, editor/dashboard, ATS, AI, import/export, automatic history, restoration or diff. Publicly exposed proxies are outside local identity assumptions. SQLite serializes writers and may return 503 under contention; no retry policy. Offset pages can shift with concurrent edits. Non-ASCII case folding is not guaranteed. Trusted direct SQL can bypass canonical rules and historical immutability. Browser visuals/accessibility and PostgreSQL are unverified. The upstream warning remains non-blocking. No later milestone was started.

## 25. Exact manual commands

From repository root in PowerShell, after existing dependency setup:

```powershell
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini current
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini check
$env:HIRESENSE_ENVIRONMENT='development'
$env:HIRESENSE_DEVELOPMENT_IDENTITY_ENABLED='true'
Set-Location backend
.venv/Scripts/python.exe -m app.initialize_owner
$env:HIRESENSE_DEVELOPMENT_OWNER_ID='<UUID printed by command>'
Set-Location ..
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --no-access-log
```

Use http://127.0.0.1:8000/docs or the synthetic examples in the [resume API guide](../architecture/resume-api.md). For independent verification:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini --basetemp backend/.local/task003-release -p no:cacheprovider --tb=short
backend/.venv/Scripts/python.exe backend/scripts/verify_resume_api.py
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe -m compileall -q backend/app backend/scripts
git diff --check
Set-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run dev
```

The implementation environment required scoped execution outside its sandbox for pytest-managed directories and disposable HTTP cleanup. Use a dedicated disposable --basetemp path because pytest clears it. The HTTP script starts/stops its own process and removes only its isolated database directory. Stop manual servers with Ctrl+C. Do not terminate unrelated processes, downgrade genuine data or publicly expose development identity.

## 26. Git handoff

Suggested commit: `feat: implement resume management services and REST APIs`.

No commit, push, remote modification, author/committer timestamp change, history rewrite or deployment occurred. Source changes remain for owner review.

## 27. Next milestone

Task 004: professional frontend design system, application shell, navigation architecture and resume library interface, only when separately authorized. Task 005 introduces the structured editor. Neither was started.
