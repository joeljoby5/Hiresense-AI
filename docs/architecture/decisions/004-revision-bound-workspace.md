# ADR 004 — Revision-bound workspace and artifacts

## Context

An interactive editor, generated documents, and saved job analyses all need a reliable source document. Multiple tabs or account sessions may edit the same draft. Rendering and scoring can take longer than basic database access on a small development machine.

## Decisions

- The backend Pydantic document remains canonical. Generate frontend editor field definitions from its JSON Schema. Keep local editor state, undo and redo separate from server cache and persistent checkpoints.
- Use the existing optimistic draft revisions for writes and current-draft exports. ATS requests identify both the resume source and the job revision. Opt-in AI suggestions reference the saved draft and require a separate user edit to apply.
- Read and validate exact sources inside a short owner-scoped transaction. Render, score or call the provider after releasing that transaction. Recheck owner and source existence before retaining generated artifacts. Use SQLite retention limits and cascading deletion for exports and analyses.
- Support authenticated cookie sessions and a distinct opt-in development owner through the same service and repository boundaries. Session state and working drafts remain in memory on the client.

## Consequences

Saved results remain attributable when source drafts change. A job or resume deletion removes associated artifacts. Browser preview pagination remains approximate. Local inference stays optional and the feature set remains usable without a model. The team can add genuine file parsing and version restoration without creating a parallel resume schema.
