from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.database.session import transaction
from app.main import create_app
from app.models import AccountSession, Resume, User
from app.security.throttle import LoginAttempts
from app.services.errors import AuthenticationBusy

ORIGIN = {"Origin": "http://127.0.0.1:5173"}
PASSWORD = "synthetic-strong-password"


def test_account_registration_session_csrf_rotation_and_deletion(database):
    settings, _, factory = database
    app = create_app(settings)
    with TestClient(app, client=("127.0.0.1", 4321)) as first, TestClient(app, client=("127.0.0.1", 4322)) as second:
        body = {"email": "Owner@Example.org", "password": PASSWORD, "display_name": "Synthetic candidate"}
        assert first.post("/api/v1/auth/register", json=body).status_code == 403
        registered = first.post("/api/v1/auth/register", headers=ORIGIN, json=body)
        assert registered.status_code == 201, registered.text
        cookie = registered.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
        csrf = {**ORIGIN, "X-CSRF-Token": registered.json()["csrf_token"]}
        assert first.get("/api/v1/auth/me").json()["profile"]["email"] == "owner@example.org"
        assert first.post("/api/v1/resumes", headers=ORIGIN, json={"title": "Wrong"}).status_code == 403
        assert first.post("/api/v1/resumes", headers={**csrf, "Origin": "https://example.org"}, json={"title": "Wrong"}).status_code == 403
        source = first.post("/api/v1/resumes", headers=csrf, json={"title": "Synthetic private draft"})
        assert source.status_code == 201, source.text
        assert first.post(source.headers["location"] + "/duplicate", headers=csrf).status_code == 201
        probe = second.post("/api/v1/auth/register", headers=ORIGIN, json={**body, "email": "other@example.org"})
        assert probe.status_code == 201
        foreign = {**ORIGIN, "X-CSRF-Token": probe.json()["csrf_token"]}
        assert second.get(source.headers["location"]).status_code == 404
        assert second.delete(source.headers["location"], headers=foreign, params={"expected_revision": 1}).status_code == 404
        assert second.get("/api/v1/resumes").json()["total"] == 0
        assert second.post("/api/v1/auth/logout", headers=foreign).status_code == 204
        password_sign_in = {key: body[key] for key in ("email", "password")}
        assert second.post("/api/v1/auth/login", headers=ORIGIN, json={**password_sign_in, "password": "wrong"}).status_code == 401
        assert second.post("/api/v1/auth/login", headers=ORIGIN, json=password_sign_in).status_code == 200
        profile = first.patch("/api/v1/auth/me", headers=csrf, json={"display_name": "Candidate Updated"})
        assert profile.json()["profile"]["display_name"] == "Candidate Updated"
        rotated = first.post("/api/v1/auth/password", headers=csrf,
                             json={"current_password": PASSWORD, "new_password": PASSWORD + "-rotated"})
        assert rotated.status_code == 200, rotated.text
        assert second.get("/api/v1/auth/me").status_code == 401
        assert first.post("/api/v1/auth/revoke-sessions", headers=csrf).status_code == 403
        csrf["X-CSRF-Token"] = rotated.json()["csrf_token"]
        revoked = first.post("/api/v1/auth/revoke-sessions", headers=csrf)
        assert revoked.status_code == 200
        csrf["X-CSRF-Token"] = revoked.json()["csrf_token"]
        with transaction(factory) as session:
            owner = session.scalar(select(User).where(User.email == "owner@example.org"))
            assert owner.password_hash.startswith("scrypt-v1$") and PASSWORD not in owner.password_hash
            assert len(session.scalars(select(AccountSession).where(AccountSession.owner_id == owner.id)).all()) == 1
        removed = first.request("DELETE", "/api/v1/auth/me", json={"password": PASSWORD + "-rotated"}, headers=csrf)
        assert removed.status_code == 204, removed.text
        assert first.get("/api/v1/auth/me").status_code == 401
        with transaction(factory) as session:
            assert session.scalar(select(User).where(User.email == "owner@example.org")) is None
            assert session.scalars(select(Resume)).all() == []


def test_https_cookie_attributes_and_http_origin_rejection(database):
    settings, _, factory = database
    app = create_app(Settings(_env_file=None, database_url=settings.database_url,
                             environment="production", allowed_origins=["https://workspace.example.org", ORIGIN["Origin"]]))
    data = {"email": "secure@example.org", "password": PASSWORD}
    with TestClient(app, base_url="https://workspace.example.org") as client:
        assert client.post("/api/v1/auth/register", headers=ORIGIN, json=data).status_code == 403
        response = client.post("/api/v1/auth/register", headers={"Origin": "https://workspace.example.org"}, json=data)
        assert response.status_code == 201
        cookie = response.headers["set-cookie"]
        assert cookie.startswith("__Host-hiresense_session=") and "Secure" in cookie and "Domain=" not in cookie
        with transaction(factory) as session:
            session.scalar(select(AccountSession)).expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        assert client.get("/api/v1/auth/me").status_code == 401


def test_attempt_budget_is_bounded_and_recovers(monkeypatch):
    now = 0.0
    monkeypatch.setattr("app.security.throttle.monotonic", lambda: now)
    budget = LoginAttempts()
    for _ in range(8):
        budget.check("example-peer")
    with pytest.raises(AuthenticationBusy):
        budget.check("example-peer")
    now = 61.0
    budget.check("example-peer")
