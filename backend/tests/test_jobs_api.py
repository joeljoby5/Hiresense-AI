from app.api.identity import resolve_owner
from test_resume_api import api
from test_resume_services import services


DETAIL = {
    "title": "Backend Intern",
    "company": "Example Studio",
    "description": "Required: basic Python skills. SQL is preferred.",
    "listing_url": "https://example.org/jobs/42",
    "notes": "Synthetic follow-up",
}


def test_job_lifecycle_and_ownership(api):
    client, owner, other = api
    prefix = "/api/v1/jobs"
    created = client.post(prefix, json=DETAIL)
    assert created.status_code == 201, created.text
    endpoint = created.headers["location"]
    assert created.json()["details"]["description"] == DETAIL["description"]
    assert created.json()["revision"] == 1
    listing = client.get(prefix, params={"search": "example", "limit": 1}).json()
    assert listing["total"] == 1 and "details" not in listing["items"][0]
    assert client.get(prefix, params={"search": "%"}).json()["total"] == 0
    assert client.get(endpoint).json() == created.json()
    updated = client.patch(endpoint, json={"expected_revision": 1, "details": {**DETAIL, "title": "Platform Intern"}})
    assert updated.status_code == 200
    stale = client.patch(endpoint, json={"expected_revision": 1, "archived": True})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "JOB_REVISION_CONFLICT"
    assert stale.json()["error"]["current_revision"] == 2
    assert client.patch(endpoint, json={"expected_revision": 2, "archived": True}).json()["archived"]
    assert client.get(prefix).json()["total"] == 0
    assert client.get(prefix, params={"archived": True}).json()["total"] == 1
    client.app.dependency_overrides[resolve_owner] = lambda: other.owner_id
    assert client.get(prefix, params={"archived": True}).json()["total"] == 0
    assert client.get(endpoint).status_code == 404
    assert client.patch(endpoint, json={"expected_revision": 3, "archived": False}).status_code == 404
    assert client.delete(endpoint, params={"expected_revision": 3}).status_code == 404
    client.app.dependency_overrides[resolve_owner] = lambda: owner.owner_id
    assert client.patch(endpoint, json={"expected_revision": 3, "archived": False}).json()["archived"] is False
    assert client.delete(endpoint, params={"expected_revision": 3}).status_code == 409
    assert client.delete(endpoint, params={"expected_revision": 4}).status_code == 204
    assert client.get(endpoint).status_code == 404


def test_job_validation(api):
    client, _, _ = api
    prefix = "/api/v1/jobs"
    for change in ({"description": " "}, {"company": "X" * 201}, {"listing_url": "javascript:alert(1)"},
                   {"notes": "X" * 5_001}, {"owner_id": "invalid"}):
        assert client.post(prefix, json={**DETAIL, **change}).status_code == 422
    created = client.post(prefix, json=DETAIL)
    endpoint = created.headers["location"]
    for change in ({}, {"archived": "true"}, {"details": {"title": "partial"}}, {"expected_revision": True}):
        assert client.patch(endpoint, json={"expected_revision": 1, **change}).status_code == 422
    assert client.get(endpoint).json()["revision"] == 1

def test_job_requirements_are_owner_scoped(api):
    client, _, other = api
    job = client.post("/api/v1/jobs", json=DETAIL)
    endpoint = job.headers["location"] + "/requirements"
    result = client.get(endpoint).json()
    assert result["extractor_version"] == "job-requirements-1"
    assert result["requirements"][0]["alternatives"] == ["python"]
    client.app.dependency_overrides[resolve_owner] = lambda: other.owner_id
    assert client.get(endpoint).status_code == 404
