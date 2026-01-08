# ADR 002: Canonical documents and lightweight relational persistence

Date: 2026-11-27. Status: accepted for Task 002.

## Context

Resume editing, ATS, import/export and later AI need the same typed content, stable identities and history. The local Windows machine has 8 GB RAM; the existing modular monolith should avoid service infrastructure. Ownership and concurrency need reliable database invariants before public workflows exist.

## Decisions

1. Use Pydantic schema-version-1 value models for canonical content, independently of HTTP/ORM. Empty drafts are valid; completeness is workflow-specific. UUID entry identities and plain structured text enable later targeted edits and comparisons. Share typed AdditionalEntry across similar extended sections; reject unknown fields rather than accepting arbitrary dictionaries.
2. Store canonical JSON inside relational resumes and immutable version records. Keep identity, ownership, timestamps and counters relational. Explicit whole-document replacement gives predictable validation and avoids SQLAlchemy in-place mutation assumptions. Tradeoff: field-level JSON querying is not optimized, and database-level JSON shape enforcement is deferred.
3. Use synchronous SQLAlchemy 2.x with built-in SQLite, explicit Alembic initialization and migrations. Resolve paths from the backend, enable foreign keys per connection, use 5s busy timeout and retain default journal mode. Restore explicit transactional BEGIN for SQLite. PostgreSQL remains a future adapter/dialect verification task, with no server or driver installed now.
4. Repositories flush only; a caller-owned transaction commits/rolls back and closes sessions. Composite parent ownership foreign keys and owner predicates protect boundaries. Development identities are internal, development-only and have no credential. Authentication remains a separate milestone.
5. Compare/increment draft revisions in an atomic conditional write. Allocate snapshot numbers with a transactional row counter and uniqueness constraint. This adds one relational counter but avoids MAX()+1 races and keeps snapshots independent of autosave. Normal ORM historical updates are rejected; trusted direct SQL remains outside this application immutability boundary.
6. Store UTC consistently through an explicit datetime type adapter; Python consumers get aware values despite SQLite's naive storage. Keep liveness unchanged and add a synchronous, generic database readiness route. Optional SQL logging suppresses parameters and result rows.

## Consequences

No external AI, database server or background infrastructure is required. The schema supports draft edits and intentional history internally, without exposing unfinished workflows. JSON validation is an application boundary; arbitrary SQL bypasses some invariants. SQLite serializes writers and may require whole-transaction retry at a future service boundary. Longer ancestry-cycle checks, snapshot restoration, authentication and database encryption/retention need explicit later decisions.
