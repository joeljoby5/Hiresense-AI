import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.contracts import InvalidProviderResponse, ProviderRateLimited, ProviderTimeout, ProviderUnavailable
from app.ai.local import LocalAIProvider, validate_local_origin
from app.api.identity import resolve_owner
from app.core.config import Settings
from app.main import create_app
from test_resume_api import api
from test_resume_services import services


def response(body, status=200):
    return httpx.Response(status, headers={"content-type": "application/json"},
                          stream=httpx.ByteStream(json.dumps(body).encode()))


@pytest.mark.parametrize(("protocol", "health", "generation"), [
    ("ollama", "/api/tags", "/api/chat"),
    ("openai-compatible", "/v1/models", "/v1/chat/completions"),
])
def test_local_contract(protocol, health, generation):
    def handle(request):
        assert request.url.host == "127.0.0.1"
        if request.method == "GET":
            assert request.url.path == health
            return response({"models": [{"name": "example"}], "data": [{"id": "example"}]})
        assert request.url.path == generation
        data = json.loads(request.content)
        assert data["model"] == "example"
        assert data["messages"][1] == {"role": "user", "content": "Synthetic summary"}
        message = {"content": json.dumps({"proposed": "Synthetic summary", "explanation": "Preserved text"})}
        return response({"message": message, "choices": [{"message": message}]})

    provider = LocalAIProvider("http://127.0.0.1:11434", "example", protocol, httpx.MockTransport(handle))
    assert provider.status().available
    assert provider.rewrite_summary("Synthetic summary").proposed == "Synthetic summary"


@pytest.mark.parametrize("origin", ["https://example.org:443", "http://localhost:11434", "http://127.0.0.1",
                                    "http://127.0.0.1:11434/api", "http://user@127.0.0.1:11434",
                                    "file://127.0.0.1:11434", "http://127.0.0.1:11434?"])
def test_local_origin_restrictions(origin):
    with pytest.raises(ValueError):
        validate_local_origin(origin)


@pytest.mark.parametrize(("status", "error"), [(429, ProviderRateLimited), (302, ProviderUnavailable),
                                                        (503, ProviderUnavailable), (200, InvalidProviderResponse)])
def test_local_provider_errors(status, error):
    provider = LocalAIProvider("http://127.0.0.1:11434", "example", "ollama",
                               httpx.MockTransport(lambda _: response({"unexpected": True}, status)))
    with pytest.raises(error):
        provider.rewrite_summary("Synthetic summary")


def test_provider_timeout():
    def timeout(_):
        raise httpx.ReadTimeout("synthetic")
    provider = LocalAIProvider("http://127.0.0.1:11434", "example", "ollama", httpx.MockTransport(timeout))
    with pytest.raises(ProviderTimeout):
        provider.rewrite_summary("Synthetic summary")


def test_mock_suggestion_is_owner_scoped_repeatable_and_read_only(api):
    client, _, other = api
    created = client.post("/api/v1/resumes", json={"title": "Synthetic", "content": {"professional_summary": "Writes   clear software."}})
    resume = created.json()
    endpoint = "/api/v1/ai/resumes/" + resume["id"] + "/summary"
    assert client.get("/api/v1/ai/status").json()["mock"] is True
    result = client.post(endpoint, json={"expected_revision": 1})
    assert result.status_code == 200, result.text
    assert result.json()["proposed"] == "Writes clear software."
    assert result.json()["mock"] and result.json()["source_revision"] == 1
    assert client.post(endpoint, json={"expected_revision": 1}).json() == result.json()
    assert client.post(endpoint, json={"expected_revision": 2}).status_code == 409
    assert client.get(created.headers["location"]).json() == resume
    client.app.dependency_overrides[resolve_owner] = lambda: other.owner_id
    assert client.post(endpoint, json={"expected_revision": 1}).status_code == 404


def test_core_resume_workflow_is_independent_of_ai(database, services):
    settings, _, _ = database
    owner, _, _ = services
    app = create_app(Settings(_env_file=None, database_url=settings.database_url, ai_provider="disabled"))
    app.dependency_overrides[resolve_owner] = lambda: owner.owner_id
    with TestClient(app) as client:
        assert client.get("/api/v1/ai/status").json()["available"] is False
        resume = client.post("/api/v1/resumes", json={"title": "Local resume", "content": {"professional_summary": "Candidate summary."}})
        resume_id = resume.json()["id"]
        assert client.post("/api/v1/ai/resumes/" + resume_id + "/summary", json={"expected_revision": 1}).status_code == 503
        assert client.post(resume.headers["location"] + "/exports", json={"expected_revision": 1, "format": "txt"}).status_code == 201
