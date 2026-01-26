"""Real HTTP smoke test; migrates only a disposable database and stops its server.

Run from the repository root: backend/.venv/Scripts/python.exe backend/scripts/verify_resume_api.py
"""
import json
import gc
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from disposable import remove_test_database

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.initialize_owner import initialize_owner


def verify():
    local = BACKEND / ".local"
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="task003-http-", dir=local) as directory:
        database = Path(directory) / "verify.sqlite3"
        settings = Settings(_env_file=None, database_url="sqlite:///" + database.as_posix(),
                            environment="development", development_identity_enabled=True, development_owner_id=None)
        migration = Config(str(BACKEND / "alembic.ini"))
        migration.attributes["settings"] = settings
        command.upgrade(migration, "head")
        owner = initialize_owner(settings)
        assert initialize_owner(settings) == owner
        # sqlite3 cursors may participate in cycles; release migration/bootstrap
        # handles before Windows attempts to remove the disposable database.
        gc.collect()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        environment = os.environ.copy()
        environment.update({"HIRESENSE_DATABASE_URL": settings.database_url,
            "HIRESENSE_ENVIRONMENT": "development", "HIRESENSE_DEVELOPMENT_IDENTITY_ENABLED": "true",
            "HIRESENSE_DEVELOPMENT_OWNER_ID": str(owner), "HIRESENSE_API_PREFIX": "/api/v1",
            "HIRESENSE_DEBUG": "false", "HIRESENSE_DATABASE_ECHO": "false"})
        args = [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(BACKEND),
                "--host", "127.0.0.1", "--port", str(port), "--no-access-log"]
        server = subprocess.Popen(args, cwd=BACKEND, env=environment, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        base = f"http://127.0.0.1:{port}"

        def http(method, path, expected, body=None):
            encoded = json.dumps(body).encode() if body is not None else None
            request = Request(base + path, data=encoded, method=method, headers={"Content-Type": "application/json"})
            try:
                response = urlopen(request, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                assert response.status == expected, f"{method} expected {expected}, got {response.status}"
                payload = response.read()
                assert response.headers.get("X-Request-ID")
                print(f"PASS {method} {path.split('?')[0]} -> {response.status}")
                return json.loads(payload) if payload else None

        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("Verification server exited before startup")
                try:
                    with urlopen(base + "/api/v1/health", timeout=0.25) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("Verification server did not start")
            http("GET", "/api/v1/health", 200)
            http("GET", "/api/v1/ready", 200)
            # HTML docs are checked independently because http() parses JSON.
            with urlopen(base + "/docs", timeout=5) as docs:
                assert docs.status == 200
            schema = http("GET", "/openapi.json", 200)
            assert "/api/v1/resumes" in schema["paths"]
            sentinel = http("POST", "/api/v1/resumes", 201, {"title": "Synthetic preservation sentinel"})
            created = http("POST", "/api/v1/resumes", 201, {"title": "Synthetic verification",
                "content": {"skills": [{"name": "Python"}], "experience": [{"start_date": {"year": 2020}}]}})
            path = "/api/v1/resumes/" + created["id"]
            assert http("GET", path, 200)["content"] == created["content"]
            updated = http("PATCH", path, 200, {"expected_revision": 1, "title": "Verified title"})
            assert updated["draft_revision"] == 2
            conflict = http("PATCH", path, 409, {"expected_revision": 1, "title": "Stale"})
            assert conflict["error"]["current_revision"] == 2
            version = http("POST", path + "/versions", 201, {"expected_revision": 2, "change_summary": "Synthetic checkpoint"})
            copy = http("POST", path + "/duplicate", 201, {})
            copy_path = "/api/v1/resumes/" + copy["id"]
            http("PATCH", copy_path, 200, {"expected_revision": 1, "content": {"professional_summary": "Independent copy"}})
            assert http("GET", path, 200)["content"] == created["content"]
            assert http("GET", path + "/versions/" + version["id"], 200)["content"] == created["content"]
            assert http("GET", path + "/versions", 200)["total"] == 1
            assert http("GET", "/api/v1/resumes", 200)["total"] == 3
            http("DELETE", path + "?expected_revision=2", 204)
            http("GET", path, 404)
            detached = http("GET", copy_path, 200)
            assert detached["parent_resume_id"] is None and detached["draft_revision"] == 3
            assert http("GET", "/api/v1/resumes/" + sentinel["id"], 200)["draft_revision"] == 1
            http("DELETE", copy_path + "?expected_revision=3", 204)
            http("DELETE", "/api/v1/resumes/" + sentinel["id"] + "?expected_revision=1", 204)
            assert http("GET", "/api/v1/resumes", 200)["total"] == 0
            print("PASS real HTTP lifecycle, stale revision, checkpoint, independent copy, preservation and cleanup")
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            gc.collect()
            remove_test_database(database)
            print("Verification server stopped; disposable database cleanup follows.")
    print("PASS disposable database directory removed")


if __name__ == "__main__":
    verify()
