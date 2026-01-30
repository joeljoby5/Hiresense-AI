# Local setup and verification

Use Windows PowerShell, Python 3.13, Node.js 22.12+ in the 22 series, and npm. The [README quickstart](../../README.md#getting-started) covers dependency installation, migrations, startup, and registration. Run the commands below from the repository root unless a command changes directories. Direct virtual environment invocation avoids PowerShell activation restrictions.

## Configuration and persistence

The default SQLite database is `backend/.local/data/hiresense.sqlite3`. Alembic creates the parent directory and manages the schema. Starting the application does not create tables. The database and its SQLite sidecar files are Git-ignored. Keep the database private and back it up as appropriate.

For custom settings, copy [`backend/.env.example`](../../backend/.env.example) to `backend/.env` and [`frontend/.env.example`](../../frontend/.env.example) to `frontend/.env`. The backend reads its environment file independently of the working directory. Process variables take precedence. Restart Vite after editing its environment file, and keep secrets out of browser-exposed `VITE_` variables.

- `HIRESENSE_DATABASE_URL` switches databases. Relative SQLite paths resolve from `backend/`. Use forward slashes for absolute Windows URLs, for example `sqlite:///D:/private/hiresense.sqlite3`.
- `HIRESENSE_DATABASE_ECHO` enables SQL statement logging with parameters hidden. Leave it off for ordinary use.
- `HIRESENSE_API_PREFIX` and `VITE_API_BASE_URL` must agree when changing the default `/api/v1` prefix.
- `API_PROXY_TARGET` points Vite to the backend. Both development servers bind to loopback. For alternate ports, set the matching backend URL in `frontend/.env`, pass `--port 5174` to Vite via `npm.cmd run dev -- --port 5174`, and add `http://127.0.0.1:5174` to the backend's exact `HIRESENSE_ALLOWED_ORIGINS` list so registration and authenticated writes work.

After changing databases or pulling schema updates, run `backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head`. Use the same command prefix with `current` to see the current revision or `check` to look for migration drift. `/api/v1/health` reports liveness, while `/api/v1/ready` checks database connectivity and schema state. Interactive API docs are at <http://127.0.0.1:8000/docs>.

Stop both development servers with Ctrl+C in their terminals. `npm.cmd run preview` serves the built frontend on port 4173 without the development API proxy. Hosted use requires production configuration, including HTTPS and either a same-origin API reverse proxy or a configured API URL and explicit origins.

## Optional development identity

Use browser registration for ordinary work. For session-free API testing, explicitly initialize and configure an independent local development owner.

```powershell
$env:HIRESENSE_ENVIRONMENT = 'development'
$env:HIRESENSE_DEVELOPMENT_IDENTITY_ENABLED = 'true'
Set-Location backend
.venv/Scripts/python.exe -m app.initialize_owner
$env:HIRESENSE_DEVELOPMENT_OWNER_ID = '<printed UUID>'
Set-Location ..
```

Start the loopback backend from the same terminal using the [quickstart command](../../README.md#getting-started). Initialization is idempotent and requires a migrated database. Keep this mode disabled in hosted environments. See the [resume API](../architecture/resume-api.md) and [account security](../architecture/accounts.md) for identity and ownership behavior.

## Writing provider settings

`HIRESENSE_AI_PROVIDER` defaults to `mock`, which normalizes whitespace in saved summaries. Set it to `disabled` to turn off writing assistance. `ollama` and `openai-compatible` require `HIRESENSE_LOCAL_AI_ORIGIN` set to a loopback IP with an explicit port and `HIRESENSE_LOCAL_AI_MODEL` matching a model in your separately installed runtime. The request sends the saved summary after the user gives consent. Automated tests cover the adapter contracts with controlled HTTP responses. Live inference requires separate verification.

## Verification

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -c backend/pytest.ini
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe backend/scripts/generate_resume_schema.py --check
backend/.venv/Scripts/python.exe backend/scripts/verify_resume_api.py
backend/.venv/Scripts/python.exe backend/scripts/verify_workspace.py
Set-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

The HTTP and browser harnesses own disposable migrated SQLite databases and loopback servers, and clean up their resources after execution. The browser harness uses Microsoft Edge on Windows and Playwright Chromium on other platforms. Keep port 5184 free while running it. If Windows denies pytest access to temporary directories, run from a terminal with permission to manage them or pass `--basetemp backend/.local/pytest-disposable -p no:cacheprovider`. Use a dedicated directory because pytest clears it.

See the [master implementation report](master-implementation-report.md) for recorded validation and [the progress tracker](master-implementation-progress.md) for open work.
