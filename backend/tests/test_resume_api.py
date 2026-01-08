from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update, text

from app.api.identity import resolve_owner
from app.core.config import Settings
from app.database.session import transaction
from app.main import create_app
from app.models import Resume, User
from app.schemas.resumes import ResumeDetailResponse, ResumeListResponse, ResumeVersionDetailResponse
from app.repositories.resumes import ResumeRepository
from test_resume_services import services  # shared isolated fixture


@pytest.fixture
def api(database, services):
    settings, _, _ = database
    a, b, _ = services
    application = create_app(settings)
    application.dependency_overrides[resolve_owner] = lambda: a.owner_id
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client, a, b


def test_complete_http_lifecycle(api):
    client, _, _ = api
    created = client.post("/api/v1/resumes", json={"title": "Synthetic \u674e", "content": {
        "skills": [{"name": "Python"}], "experience": [{"start_date": {"year": 2020}}]}})
    assert created.status_code == 201
    item = ResumeDetailResponse.model_validate(created.json())
    path = created.headers["location"]
    assert item.draft_revision == 1 and item.created_at.utcoffset().total_seconds() == 0
    assert item.content.experience[0].start_date.month is None
    assert client.get(path).json() == created.json()
    assert "owner_id" not in created.json()
    title_edit = client.patch(path, json={"title": "Updated", "expected_revision": 1})
    assert title_edit.status_code == 200 and title_edit.json()["draft_revision"] == 2
    stale = client.patch(path, json={"title": "Stale", "expected_revision": 1})
    assert stale.status_code == 409
    assert stale.json()["error"]["current_revision"] == 2
    assert stale.json()["error"]["request_id"] == stale.headers["x-request-id"]
    content_edit = client.patch(path, json={"content": {"professional_summary": "Updated content"}, "expected_revision": 2})
    assert content_edit.status_code == 200
    assert content_edit.json()["content"]["skills"] == []  # full replacement
    version = client.post(path + "/versions", json={"expected_revision": 3, "change_summary": "Checkpoint"})
    assert version.status_code == 201
    ResumeVersionDetailResponse.model_validate(version.json())
    assert client.get(version.headers["location"]).json() == version.json()
    assert client.post(path + "/versions", json={"expected_revision": 2}).status_code == 409
    assert client.get(path + "/versions").json()["total"] == 1
    assert "content" not in client.get(path + "/versions").json()["items"][0]
    copied = client.post(path + "/duplicate")
    assert copied.status_code == 201
    copy_path = copied.headers["location"]
    assert client.get(copy_path + "/versions").json()["total"] == 0
    assert client.patch(copy_path, json={"expected_revision": 1, "content": {"professional_summary": "Copy"}}).status_code == 200
    assert client.get(path).json()["content"]["professional_summary"] == "Updated content"
    page = client.get("/api/v1/resumes")
    ResumeListResponse.model_validate(page.json())
    assert page.json()["total"] == 2 and "content" not in page.json()["items"][0]
    assert client.delete(path, params={"expected_revision": 2}).status_code == 409
    deleted = client.delete(path, params={"expected_revision": 3})
    assert deleted.status_code == 204 and deleted.content == b""
    assert client.get(path).status_code == 404
    assert client.get(copy_path).json()["parent_resume_id"] is None
    assert client.get(copy_path).json()["draft_revision"] == 3
    assert client.delete(copy_path, params={"expected_revision": 3}).status_code == 204


@pytest.mark.parametrize("body", [{}, {"title": ""}, {"title": " "}, {"title": "x" * 201},
    {"title": "X", "owner_id": str(uuid4())}, {"title": "X", "draft_revision": 2},
    {"title": "X", "id": str(uuid4())}, {"title": "X", "created_at": "2020-01-01"},
    {"title": "X", "content": None}, {"title": "X", "content": {"schema_version": 2}},
    {"title": "X", "content": {"personal_information": {"email": "private-invalid-email"}}},
    {"title": "X", "content": {"skills": [{"name": "X"}] * 201}}])
def test_invalid_create_requests(api, body):
    client, _, _ = api
    response = client.post("/api/v1/resumes", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["fields"]
    assert "private-invalid-email" not in response.text
    assert client.get("/api/v1/resumes").json()["total"] == 0


@pytest.mark.parametrize("body", [{}, {"title": "New"}, {"expected_revision": 1},
    {"expected_revision": 1, "title": None}, {"expected_revision": 1, "content": None},
    {"expected_revision": 1, "content": {"unknown": 1}}, {"expected_revision": 0, "title": "X"},
    {"expected_revision": True, "title": "X"}, {"expected_revision": "1", "title": "X"},
    {"expected_revision": 1, "title": "X", "owner_id": str(uuid4())},
    {"expected_revision": 1, "title": "X", "parent_resume_id": str(uuid4())},
    {"expected_revision": 1, "title": "X", "next_version_number": 9}])
def test_invalid_update_requests(api, body):
    client, a, _ = api
    item = a.create("Original")
    response = client.patch(f"/api/v1/resumes/{item.id}", json=body)
    assert response.status_code == 422
    assert a.get(item.id).title == "Original" and a.get(item.id).draft_revision == 1


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "offset=1000001", "search=" + "x" * 201,
                                 "sort=unknown", "owner_id=" + str(uuid4())])
def test_invalid_list_queries(api, query):
    assert api[0].get("/api/v1/resumes?" + query).status_code == 422


def test_search_pagination_stable_sort_and_literal_wildcards(api):
    client, a, b = api
    for title in ["Alpha", "alpha percent%", "under_score", "slash/", "Same", "Same"]:
        a.create(title)
    b.create("Alpha foreign")
    for query, count in [("ALPHA", 2), ("%", 1), ("_", 1), ("/", 1), ("' OR 1=1 --", 0)]:
        page = client.get("/api/v1/resumes", params={"search": query}).json()
        assert page["total"] == count
    first = client.get("/api/v1/resumes", params={"search": "Same", "sort": "title_asc", "limit": 1}).json()
    second = client.get("/api/v1/resumes", params={"search": "Same", "sort": "title_asc", "limit": 1, "offset": 1}).json()
    assert first["total"] == 2 and first["has_more"] and not second["has_more"]
    assert first["items"][0]["id"] < second["items"][0]["id"]
    default = client.get("/api/v1/resumes").json()
    assert default["limit"] == 20 and default["offset"] == 0 and default["total"] == 6


@pytest.mark.parametrize("operation", ["get", "patch", "delete", "duplicate", "checkpoint", "versions", "version"])
def test_cross_owner_access_matches_unknown_resources(api, operation):
    client, a, b = api
    private = b.create("Foreign private")
    checkpoint = b.checkpoint(private.id, 1)

    def request(resume_id):
        path = f"/api/v1/resumes/{resume_id}"
        if operation == "get":
            return client.get(path)
        if operation == "patch":
            return client.patch(path, json={"title": "Attack", "expected_revision": 1})
        if operation == "delete":
            return client.delete(path, params={"expected_revision": 1})
        if operation == "duplicate":
            return client.post(path + "/duplicate", json={})
        if operation == "checkpoint":
            return client.post(path + "/versions", json={"expected_revision": 1})
        if operation == "versions":
            return client.get(path + "/versions")
        return client.get(path + f"/versions/{checkpoint.id}")

    foreign, unknown = request(private.id), request(uuid4())
    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json()["error"]["code"] == unknown.json()["error"]["code"] == "RESUME_NOT_FOUND"
    assert a.list().total == 0 and b.get(private.id).title == "Foreign private"


def test_version_association_missing_uuids_and_version_pagination(api):
    client, a, _ = api
    first, second = a.create("First"), a.create("Second")
    versions = [a.checkpoint(first.id, 1) for _ in range(3)]
    wrong = client.get(f"/api/v1/resumes/{second.id}/versions/{versions[0].id}")
    assert wrong.status_code == 404 and wrong.json()["error"]["code"] == "RESUME_VERSION_NOT_FOUND"
    page = client.get(f"/api/v1/resumes/{first.id}/versions?limit=1&offset=1").json()
    assert page["total"] == 3 and page["items"][0]["version_number"] == 2 and page["has_more"]
    assert client.get("/api/v1/resumes/not-a-uuid").status_code == 422
    assert client.get(f"/api/v1/resumes/{first.id}/versions/not-a-uuid").status_code == 422
    assert client.delete(f"/api/v1/resumes/{first.id}").status_code == 422
    assert client.get(f"/api/v1/resumes/{first.id}/versions?limit=101").status_code == 422
    assert client.post(f"/api/v1/resumes/{first.id}/versions", json={"expected_revision": 1, "change_summary": "x" * 501}).status_code == 422
    assert client.post(f"/api/v1/resumes/{first.id}/duplicate", json={"title": None}).status_code == 422
    custom = client.post(f"/api/v1/resumes/{first.id}/duplicate", json={"title": "Custom"})
    assert custom.status_code == 201 and custom.json()["title"] == "Custom"


@pytest.mark.parametrize("mode", ["disabled", "production", "missing-config", "missing-owner", "inactive", "remote", "enabled"])
def test_real_identity_resolution_fails_closed(database, services, mode):
    settings, _, factory = database
    a, b, _ = services
    settings.development_identity_enabled = mode != "disabled"
    settings.development_owner_id = None if mode == "missing-config" else uuid4() if mode == "missing-owner" else a.owner_id
    if mode == "production":
        settings.environment = "production"
    if mode == "inactive":
        with transaction(factory) as session:
            session.execute(update(User).where(User.id == a.owner_id).values(is_active=False))
    peer = "203.0.113.10" if mode == "remote" else "127.0.0.1"
    with TestClient(create_app(settings), client=(peer, 50000)) as client:
        response = client.get("/api/v1/resumes", headers={"Host": "localhost", "X-Owner-ID": str(b.owner_id),
                             "X-Forwarded-For": "127.0.0.1"})
        if mode == "enabled":
            assert response.status_code == 200
            made = client.post("/api/v1/resumes", json={"title": "Local"}, headers={"X-Owner-ID": str(b.owner_id)})
            assert made.status_code == 201
            assert a.list().total == 1 and b.list().total == 0
        else:
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "DEVELOPMENT_IDENTITY_UNAVAILABLE"
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/ready").status_code == 200


def test_errors_privacy_logging_correlation_and_payload_limits(api, caplog, monkeypatch):
    import logging
    client, a, _ = api
    private = "synthetic-private-value"
    with caplog.at_level(logging.INFO, logger="hiresense.requests"):
        response = client.post("/api/v1/resumes", json={"title": "Private", "content": {"professional_summary": private}},
                               headers={"X-Request-ID": "client-controlled"})
        client.get("/api/v1/resumes", params={"search": private})
    assert response.status_code == 201
    request_id = response.headers["x-request-id"]
    assert len(request_id) == 32 and request_id != "client-controlled"
    safe_logs = " ".join(record.getMessage() for record in caplog.records if record.name == "hiresense.requests")
    assert request_id in safe_logs and private not in safe_logs
    too_large = client.post("/api/v1/resumes", content=b" " * 1_048_577)
    assert too_large.status_code == 413
    assert too_large.json()["error"]["request_id"] == too_large.headers["x-request-id"]
    malformed = client.post("/api/v1/resumes", content=b'{"title":')
    assert malformed.status_code == 422 and "input" not in malformed.text

    def fail(*args, **kwargs):
        raise RuntimeError(private)

    monkeypatch.setattr(ResumeRepository, "page", fail)
    error = client.get("/api/v1/resumes")
    assert error.status_code == 500 and error.json()["error"]["code"] == "INTERNAL_ERROR"
    assert private not in error.text


def test_database_failure_and_corrupt_document_responses(api, database):
    client, a, _ = api
    _, _, factory = database
    item = a.create("Corrupt")
    with transaction(factory) as session:
        session.execute(update(Resume).where(Resume.id == item.id).values(draft_content={"schema_version": 9}))
    response = client.get(f"/api/v1/resumes/{item.id}")
    assert response.status_code == 500 and "schema_version" not in response.text
    with transaction(factory) as session:
        session.execute(text("DROP TABLE resume_versions"))
    response = client.get(f"/api/v1/resumes/{item.id}/versions")
    assert response.status_code == 503 and response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "SELECT" not in response.text


def test_openapi_and_mutation_cors(api):
    client, _, _ = api
    schema = client.get("/openapi.json").json()
    for path in ("/api/v1/resumes", "/api/v1/resumes/{resume_id}", "/api/v1/resumes/{resume_id}/duplicate",
                 "/api/v1/resumes/{resume_id}/versions", "/api/v1/resumes/{resume_id}/versions/{version_id}"):
        assert path in schema["paths"]
    assert "409" in schema["paths"]["/api/v1/resumes/{resume_id}"]["patch"]["responses"]
    response = client.options("/api/v1/resumes", headers={"Origin": "http://localhost:5173",
                              "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_two_http_clients_cannot_overwrite_same_revision(api):
    first, a, _ = api
    item = a.create("Shared draft")
    path = f"/api/v1/resumes/{item.id}"
    second = TestClient(first.app)
    revision_a = first.get(path).json()["draft_revision"]
    revision_b = second.get(path).json()["draft_revision"]
    assert revision_a == revision_b == 1
    assert first.patch(path, json={"expected_revision": revision_a, "title": "Client A"}).status_code == 200
    assert second.patch(path, json={"expected_revision": revision_b, "title": "Client B"}).status_code == 409
    assert a.get(item.id).title == "Client A"


def test_integrity_failure_is_safe_and_rolls_back(api, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    client, a, _ = api
    original = ResumeRepository.create

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise IntegrityError("private-statement", {"private": "private-value"}, Exception("private-cause"))

    monkeypatch.setattr(ResumeRepository, "create", fail)
    response = client.post("/api/v1/resumes", json={"title": "Rollback"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private" not in response.text
    assert a.list().total == 0


def test_streamed_body_limit_without_trusting_content_length():
    import asyncio
    from app.core.request_context import RequestContextMiddleware

    async def run():
        reached_application = False

        async def application(scope, receive, send):
            nonlocal reached_application
            reached_application = True

        messages = iter([
            {"type": "http.request", "body": b"x" * 600_000, "more_body": True},
            {"type": "http.request", "body": b"x" * 600_000, "more_body": False},
        ])
        replies = []

        async def receive():
            return next(messages)

        async def send(message):
            replies.append(message)

        scope = {"type": "http", "method": "POST", "headers": [(b"content-length", b"1")]}
        await RequestContextMiddleware(application)(scope, receive, send)
        assert not reached_application
        assert replies[0]["status"] == 413
        assert b"REQUEST_TOO_LARGE" in replies[1]["body"]

    asyncio.run(run())
