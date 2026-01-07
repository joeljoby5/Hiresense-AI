# Initial architecture

## Purpose and current scope

HireSense AI is planned as a career intelligence platform for resume creation, ATS optimization and career development. Task 001 implements the foundation only: a React screen communicating with a FastAPI health endpoint. The API has centralized validated settings, a typed response, explicit local CORS, OpenAPI documentation and basic lifecycle logging.

## Modular monolith

```mermaid
flowchart LR
  Browser[React presentation] --> Client[Typed API client]
  Client -->|/api/v1 through local Vite proxy| API[FastAPI REST routes]
  API --> Settings[Settings and response schemas]
  API -. future .-> Services[Application services]
  Services -.-> Domain[Resume domain and deterministic intelligence]
  Services -.-> Data[Data access: SQLAlchemy / SQLite]
  Services -.-> Adapters[Document and optional AI provider adapters]
```

Solid connections are implemented; dashed connections are plans. Browser presentation and HTTP transport are separated. The application factory accepts explicit settings, allowing tests to vary version, environment, namespace and allowed origins without mutating global configuration. The health route reports configuration only; it does not imply subsystem readiness.

Future business rules belong in application/domain code, independent of React, HTTP routing, storage implementations and AI vendors. Add these layers when actual behavior needs them. A health route does not warrant placeholder service or repository abstractions.

## Planned persistence

SQLite will support local development through SQLAlchemy, with Alembic-managed migrations. PostgreSQL can be considered later if concurrency and deployment requirements justify it. Task 001 creates no database files, models, migrations or persistence dependencies. Canonical resume modeling is explicitly deferred to the next authorized task.

## Planned modules and integrations

Planned modules include resume management/versioning, document parsing/generation, deterministic ATS compatibility, job description intelligence, skill normalization/gaps, writing assistance, interview preparation, application tracking and career analytics. These are objectives, not completed capabilities.

External AI should sit behind provider adapters, configurable for local or cloud inference when separately authorized. Deterministic ATS, resume management and document generation must work without generative AI. No AI provider, model, mock generation or external inference call exists now.

## Hardware, privacy and deployment

Develop on Windows with 8 GB RAM and integrated graphics. Run two lightweight loopback servers and use an isolated Python environment. Avoid containers, heavyweight NLP/ML, persistent background services and premature infrastructure.

Frontend requests are relative by default; the development proxy forwards `/api` to loopback port 8000. The public API base is configurable for future deployments. Production hosting must explicitly route API requests; Vite's proxy is development-only. CORS uses explicit origins, with no credentials or wildcard origin by default. Time-bounded requests, runtime response validation, and no success simulation keep connectivity feedback truthful.

No secrets or personal resume data are required for this milestone. Future features must validate uploads, minimize stored personal information, protect authorization boundaries and avoid logging personal document contents. Authentication, deployment and production hardening are not claimed as implemented.
