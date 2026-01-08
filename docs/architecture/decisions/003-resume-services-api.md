# ADR 003: Local resume workflows, transactions and revision policy

Date: 2026-11-27. Status: accepted for Task 003.

## Context

Task 002 provides canonical JSON, ownership, conditional draft writes and snapshots. Task 003 needs a secure local API without introducing full authentication or changing the database schema. The laptop remains Windows with 8 GB RAM.

## Decisions

1. Keep synchronous routes thin. A focused ResumeService coordinates workflows and exposes explicit typed results. It depends on the existing repository through a structural ResumeStore interface and an injected transaction scope, without FastAPI or SQLAlchemy dependencies. Infrastructure implements the scope, checks active ownership, commits/rolls back and closes sessions.
2. Reserve SQLite writes with BEGIN IMMEDIATE before service identity/source reads. Preserve ordinary BEGIN for existing callers and reads. Continue conditional revision predicates; writer reservation complements rather than replaces atomic concurrency protection. Keep the five-second timeout and return a safe 503 instead of speculative retry machinery.
3. Default development identity off. Require an explicit development environment, enabled flag, configured existing active User and loopback peer. Provide an idempotent CLI bootstrap; never seed during HTTP requests. Identity headers and owner payloads are not authentication. Full authentication remains deferred; public exposure is prohibited.
4. Treat title/content/visible lineage as one mutable resource revision. Every PATCH increments once. Require expected_revision for PATCH, DELETE and checkpoint creation. Return 409/current revision for stale requests. Replace complete canonical JSON and keep historical checkpoints explicit.
5. Copy validated content and document-scoped entry IDs into a new independent draft with source lineage, without snapshots. For parent deletion, transactionally detach direct children, advancing their revisions, then delete the parent and its cascading versions. Preserve child documents/checkpoints and grandchildren. This resolves ADR 002's deferred parent-deletion policy without modifying its historical migration or raw SQL RESTRICT constraints.
6. Bound pagination, search, streamed bodies and canonical collections. Use metadata-only list queries, bound literal substring search and deterministic ordering. Preserve schema v1 and document the validation tightening for oversized preexisting JSON.
7. Use safe typed error envelopes and server-generated request IDs. Log route templates without query/body values. Disable raw Uvicorn access logs and HTTP tracebacks; preserve SQL parameter/result suppression.

## Consequences

All workflows run locally without new dependencies, services or schema migrations. Service tests and isolated real-HTTP verification cover transaction rollback, security boundaries and lifecycle behavior. SQLite remains a single-writer database, and offset pages can shift under concurrent changes. Deleting a parent clears lineage permanently and can invalidate a child's previously observed revision. Development identity is a temporary single-owner boundary, not public authentication. Snapshot restoration, editor/dashboard, import/export, ATS, AI and deployment remain later milestones.
