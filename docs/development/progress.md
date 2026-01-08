# Development progress

Updated: 2026-11-27 (Asia/Calcutta).

## Current milestone

Task 003: resume management application services, REST API and explicit checkpoints. Implementation and supported verification complete. Scope stops before Task 004.

## Implemented

Task 001's React/TypeScript/Vite/Tailwind frontend, typed health client and FastAPI foundation are preserved. Task 002's canonical model, SQLite entities, repositories, UTC conventions and migrations are preserved.

Task 003 adds typed synchronous HTTP routes calling application services through an injected transaction scope and structural repository boundary. Implemented: owner-scoped create/get/list/search/sort, atomic title/content edits, revision-protected hard deletion, independent duplication and checkpoint create/list/get. Title/content share one revision. Parent deletion preserves independent children and their checkpoints, clears direct lineage and advances child revisions. Ordinary edits never create snapshots.

Development identity is default-off and requires explicit development settings, configured active User and loopback peer. The idempotent CLI bootstrap is separate from requests. There is no authentication or public deployment support. Bodies, collections, search and pagination are bounded; safe errors/logs omit private input and SQL details. Request IDs are server-generated.

## Actual validation

| Check | Result |
| --- | --- |
| Baseline | 63 passed, one existing warning; Windows sandbox temp-directory restrictions resolved by scoped execution outside sandbox |
| Final backend | **139 passed**, 9.44s; one existing Starlette/HTTPX warning |
| Ownership | Cross-owner CRUD/copy/checkpoint/history blocked; headers/payloads cannot override ownership |
| Concurrency | Simultaneous service writers reject a stale revision; two HTTP clients cannot overwrite the same revision |
| Transactions | Partial copy/snapshot/delete/integrity failures roll back writes and counters |
| Migrations | Still 0001_resume_foundation; temporary upgrade/downgrade/re-upgrade and metadata check pass; no new migration |
| Real HTTP | Disposable migrated database; complete lifecycle, stale 409, snapshot/copy independence, preserved sentinel and cleanup passed |
| Identity | Disabled/production/missing/inactive/remote contexts fail closed; configured loopback works; bootstrap idempotent |
| Privacy/bounds | Safe errors/logging, corrupt content, nested/streamed limits and generated correlation tested |
| Frontend | TypeScript, ESLint, production build passed; source/config/dependencies unchanged |
| Live connectivity | Actual TypeScript health client -> Vite 5183 -> Uvicorn 8013 passed; HTML/docs/schema 200 |
| Dependencies / syntax | pip check and compileall passed; no dependencies added |
| Whitespace | git diff --check passed; non-blocking LF/CRLF normalization notice |
| Teardown | No listeners on owned 8013/5183; HTTP child stopped; unrelated processes preserved |
| Unverified | Rendered browser/accessibility and PostgreSQL |

The first HTTP lifecycle passed but transient Windows SQLite handles blocked disposable-directory cleanup. The harness now collects bootstrap/migration sqlite3 cycles; rerun passed including removal. The first leftover synthetic directory was separately removed. Genuine data was not used for test resumes or downgraded, and no development owner was seeded there.

## Limitations and handoff

One local configured owner without login; no public deployment. SQLite remains a single-writer database and may return 503 after timeout. Trusted SQL can bypass canonical validation and snapshot immutability. No database encryption, editor/dashboard, import/export, ATS, AI, restoration/diff or automatic history. New bounds can reject oversized preexisting JSON; stored content is never silently rewritten.

See [Task 003 report](task-003-report.md), [API architecture](../architecture/resume-api.md), [ADR 003](../architecture/decisions/003-resume-services-api.md) and historical [Task 002 report](task-002-report.md). Next separately authorized milestone: Task 004 design system/application shell/navigation/resume library. No commit, push or deployment occurred.
