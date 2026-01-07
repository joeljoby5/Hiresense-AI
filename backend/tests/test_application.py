import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None, app_name="HireSense AI Test", app_version="0.1.99",
        environment="test", api_prefix="/api/v1", debug=False,
        allowed_origins=["http://localhost:5173"],
    )


def test_health_uses_configuration(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "application": settings.app_name,
        "version": settings.app_version, "environment": settings.environment,
    }


def test_docs_and_openapi(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
    assert "/api/v1/health" in schema["paths"]
    assert schema["info"]["version"] == settings.app_version


def test_missing_route(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/missing").status_code == 404


@pytest.mark.parametrize("origin,allowed", [
    ("http://localhost:5173", True), ("https://untrusted.example", False),
])
def test_cors(settings: Settings, origin: str, allowed: bool) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health", headers={"Origin": origin})
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed


def test_configurable_route(settings: Settings) -> None:
    settings.api_prefix = "/api/v2"
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v2/health").status_code == 200
        assert client.get("/api/v1/health").status_code == 404


@pytest.mark.parametrize("origin", ["*", "https://example.com/path", "ftp://example.com"])
def test_invalid_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_origins=[origin])


def test_settings_ignore_unrelated_debug_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "release")
    monkeypatch.setenv("HIRESENSE_DEBUG", "true")
    monkeypatch.setenv("HIRESENSE_ENVIRONMENT", "integration")
    settings = Settings(_env_file=None)
    assert settings.debug is True
    assert settings.environment == "integration"
