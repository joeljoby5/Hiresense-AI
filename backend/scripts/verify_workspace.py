"""Run browser tests with an isolated, migrated loopback backend."""
import gc
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import urlopen

from disposable import remove_test_database

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.initialize_owner import initialize_owner


def verify() -> int:
    local = BACKEND / ".local"
    local.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="workspace-e2e-", dir=local) as directory:
        database = Path(directory) / "test.sqlite3"
        database_url = "sqlite:///" + database.as_posix()
        settings = Settings(_env_file=None, database_url=database_url, environment="development",
                            development_identity_enabled=True, development_owner_id=None)
        migration = Config(str(BACKEND / "alembic.ini"))
        migration.attributes["settings"] = settings
        command.upgrade(migration, "head")
        owner = initialize_owner(settings)
        gc.collect()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        env = {**os.environ, "HIRESENSE_DATABASE_URL": database_url, "HIRESENSE_ENVIRONMENT": "development",
               "HIRESENSE_DEVELOPMENT_IDENTITY_ENABLED": "true", "HIRESENSE_DEVELOPMENT_OWNER_ID": str(owner),
               "HIRESENSE_API_PREFIX": "/api/v1", "HIRESENSE_DEBUG": "false", "HIRESENSE_DATABASE_ECHO": "false",
               "HIRESENSE_AI_PROVIDER": "mock",
               "HIRESENSE_ALLOWED_ORIGINS": '["http://127.0.0.1:5184"]',
               "API_PROXY_TARGET": origin, "VITE_API_BASE_URL": "/api/v1"}
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
            cwd=BACKEND, env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = monotonic() + 25
            while True:
                if server.poll() is not None or monotonic() >= deadline:
                    raise RuntimeError("Browser test backend did not start")
                try:
                    with urlopen(origin + "/api/v1/ready", timeout=0.5) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError):
                    sleep(0.1)
            return subprocess.run(
                ["node", "node_modules/playwright/cli.js", "test", *sys.argv[1:]],
                cwd=BACKEND.parent / "frontend", env=env, check=False,
            ).returncode
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            gc.collect()
            remove_test_database(database)


if __name__ == "__main__":
    raise SystemExit(verify())
