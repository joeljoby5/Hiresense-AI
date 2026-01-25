from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from threading import Barrier
from uuid import uuid4
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.exc import IntegrityError
from app.core.config import Settings, BACKEND_ROOT
from app.database.session import build_engine, session_factory, transaction
from app.domain.resume.models import ResumeDocument
from app.main import create_app
from app.models import User, Resume, ResumeVersion
from app.repositories.users import UserRepository
from app.repositories.resumes import ResumeRepository
from app.repositories.errors import NotFoundError, RevisionConflictError
from conftest import migration_config


def seed(factory):
    with transaction(factory) as session:
        user = UserRepository(session).create_development_owner(" Synthetic@Example.org ", Settings(_env_file=None, environment="development"))
        other = UserRepository(session).create_development_owner("other@example.org", Settings(_env_file=None, environment="development"))
        resume = ResumeRepository(session).create(user.id, " Example ", ResumeDocument())
        return user.id, other.id, resume.id


def test_engine_connections_sessions_and_paths(database, monkeypatch, tmp_path):
    settings, engine, factory = database
    with engine.connect() as first, engine.connect() as second:
        assert first.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert second.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert second.execute(text("PRAGMA busy_timeout")).scalar() == 5000
    monkeypatch.chdir(tmp_path)
    relative = build_engine(Settings(_env_file=None, database_url="sqlite:///.local/path-test.sqlite3"))
    assert relative.url.database == (BACKEND_ROOT / ".local/path-test.sqlite3").as_posix()
    relative.dispose()
    memory = build_engine(Settings(_env_file=None, database_url="sqlite:///:memory:"))
    with memory.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar() == 1
    memory.dispose()
    with transaction(factory) as session:
        assert session.is_active
    assert not session.in_transaction()
    assert engine.pool.checkedout() == 0


def test_owner_normalization_and_unique_email(database):
    _, _, factory = database
    owner, _, _ = seed(factory)
    with transaction(factory) as session:
        item = UserRepository(session).get(owner)
        assert item.email == "synthetic@example.org"
        assert item.password_hash is None
        assert item.created_at.tzinfo == timezone.utc
    with pytest.raises(IntegrityError), transaction(factory) as session:
        UserRepository(session).create_development_owner("SYNTHETIC@example.org", Settings(_env_file=None, environment="development"))
    with pytest.raises(ValueError), transaction(factory) as session:
        UserRepository(session).create_development_owner("new@example.org", Settings(_env_file=None, environment="production"))


def test_resume_ownership_and_atomic_revisions(database):
    _, _, factory = database
    owner, other, resume_id = seed(factory)
    with transaction(factory) as session:
        repo = ResumeRepository(session)
        assert len(repo.list(owner)) == 1
        assert repo.list(other) == []
        assert repo.document(owner, resume_id) == ResumeDocument()
        assert repo.get(owner, resume_id).title == "Example"
        for operation in [lambda: repo.get(other, resume_id),
                          lambda: repo.update_draft(other, resume_id, ResumeDocument(), 1),
                          lambda: repo.create_snapshot(other, resume_id)]:
            with pytest.raises(NotFoundError):
                operation()
        updated = repo.update_draft(owner, resume_id, ResumeDocument(professional_summary="Synthetic update"), 1)
        assert updated.draft_revision == 2
        assert repo.document(owner, resume_id).professional_summary == "Synthetic update"
        with pytest.raises(RevisionConflictError):
            repo.update_draft(owner, resume_id, ResumeDocument(), 1)
        assert session.scalar(select(ResumeVersion)) is None
    with transaction(factory) as session:
        assert ResumeRepository(session).get(owner, resume_id).draft_revision == 2


def test_foreign_keys_and_parent_constraints(database):
    _, _, factory = database
    owner, other, resume_id = seed(factory)
    with pytest.raises(IntegrityError), transaction(factory) as session:
        ResumeRepository(session).create(uuid4(), "No owner", ResumeDocument())
    with pytest.raises(NotFoundError), transaction(factory) as session:
        ResumeRepository(session).create(other, "Cross owner", ResumeDocument(), resume_id)
    for parent, target_owner in [(resume_id, other), (resume_id, owner)]:
        with pytest.raises(IntegrityError), transaction(factory) as session:
            # Direct SQL tests prove constraints independently of repository checks.
            session.execute(update(Resume).where(Resume.id == resume_id).values(parent_resume_id=parent, owner_id=target_owner))
    with transaction(factory) as session:
        child = ResumeRepository(session).create(owner, "Child", ResumeDocument(), resume_id)
        child_id = child.id
    with pytest.raises(IntegrityError), transaction(factory) as session:
        session.execute(update(Resume).where(Resume.id == child_id).values(owner_id=other))
    with pytest.raises(IntegrityError), transaction(factory) as session:
        session.execute(delete(Resume).where(Resume.id == resume_id))
    with pytest.raises(IntegrityError), transaction(factory) as session:
        session.execute(delete(User).where(User.id == owner))


def test_snapshots_independence_immutability_and_delete(database):
    _, _, factory = database
    owner, other, resume_id = seed(factory)
    with transaction(factory) as session:
        repo = ResumeRepository(session)
        one = repo.create_snapshot(owner, resume_id, "Synthetic initial state")
        two = repo.create_snapshot(owner, resume_id)
        assert (one.version_number, two.version_number) == (1, 2)
        assert one.source_draft_revision == 1
        repo.update_draft(owner, resume_id, ResumeDocument(professional_summary="Edited"), 1)
        assert repo.version_document(owner, resume_id, 1).professional_summary == ""
        detached = repo.version_document(owner, resume_id, 1)
        detached.professional_summary = "Local mutation"
        assert repo.version_document(owner, resume_id, 1).professional_summary == ""
        with pytest.raises(NotFoundError):
            repo.get_version(other, resume_id, 1)
    with pytest.raises(ValueError, match="immutable"), transaction(factory) as session:
        item = ResumeRepository(session).get_version(owner, resume_id, 1)
        item.change_summary = "Attempted replacement"
    with pytest.raises(IntegrityError), transaction(factory) as session:
        session.add(ResumeVersion(resume_id=resume_id, version_number=1, source_draft_revision=1,
                                  schema_version=1, content={}))
        session.flush()
    with transaction(factory) as session:
        session.execute(delete(Resume).where(Resume.id == resume_id))
        assert session.scalar(select(ResumeVersion)) is None


def test_transaction_rollback_and_counter_rollback(database):
    _, engine, factory = database
    owner, _, resume_id = seed(factory)
    with pytest.raises(RuntimeError), transaction(factory) as session:
        repo = ResumeRepository(session)
        repo.update_draft(owner, resume_id, ResumeDocument(professional_summary="Must roll back"), 1)
        repo.create_snapshot(owner, resume_id)
        raise RuntimeError("Synthetic failure")
    with transaction(factory) as session:
        repo = ResumeRepository(session)
        assert repo.get(owner, resume_id).draft_revision == 1
        assert repo.document(owner, resume_id).professional_summary == ""
        assert repo.create_snapshot(owner, resume_id).version_number == 1
    assert engine.pool.checkedout() == 0


def test_concurrent_updates_reject_lost_write(database):
    _, _, factory = database
    owner, _, resume_id = seed(factory)
    barrier = Barrier(2)
    def write(label):
        barrier.wait(timeout=10)
        try:
            with transaction(factory) as session:
                ResumeRepository(session).update_draft(owner, resume_id, ResumeDocument(professional_summary=label), 1)
            return "updated"
        except RevisionConflictError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["First synthetic update", "Second synthetic update"]))
    assert sorted(results) == ["conflict", "updated"]


def test_concurrent_snapshots_allocate_distinct_numbers(database):
    _, _, factory = database
    owner, _, resume_id = seed(factory)
    barrier = Barrier(2)
    def snapshot(_):
        barrier.wait(timeout=10)
        with transaction(factory) as session:
            return ResumeRepository(session).create_snapshot(owner, resume_id).version_number
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(snapshot, range(2))) == [1, 2]


def test_migration_upgrade_downgrade_reupgrade(database):
    settings, engine, _ = database
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "users", "resumes", "resume_versions", "resume_exports", "jobs", "ats_analyses", "account_sessions", "alembic_version",
    }
    assert any(fk["constrained_columns"] == ["parent_resume_id", "owner_id"] for fk in inspector.get_foreign_keys("resumes"))
    assert len(inspector.get_foreign_keys("resume_versions")) == 1
    assert {"column_names": ["resume_id", "version_number"], "name": "uq_resume_versions_resume_id_version_number"} in inspector.get_unique_constraints("resume_versions")
    assert any(index["column_names"] == ["owner_id", "updated_at"] for index in inspector.get_indexes("resumes"))
    assert any(item["column_names"] == ["email"] for item in inspector.get_unique_constraints("users"))
    command.check(migration_config(settings))
    engine.dispose()
    command.downgrade(migration_config(settings), "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
    command.upgrade(migration_config(settings), "head")
    assert "resumes" in inspect(engine).get_table_names()
    command.check(migration_config(settings))


def test_upgrade_preserves_legacy_workspace_rows(tmp_path):
    settings = Settings(_env_file=None, database_url="sqlite:///" + (tmp_path / "legacy.sqlite3").as_posix())
    migration = migration_config(settings)
    command.upgrade(migration, "0001_resume_foundation")
    engine = build_engine(settings)
    owner, resume = uuid4(), uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id, email, is_active, created_at, updated_at) "
                "VALUES (:id, :email, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ), {"id": owner.hex, "email": "legacy@example.org"})
            connection.execute(text(
                "INSERT INTO resumes (id, owner_id, title, draft_content, draft_revision, next_version_number, created_at, updated_at) "
                "VALUES (:id, :owner, :title, :content, 2, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ), {"id": resume.hex, "owner": owner.hex, "title": "Legacy draft", "content": "{}"})
        command.upgrade(migration, "head")
        with engine.connect() as connection:
            user = connection.execute(text("SELECT email, display_name FROM users WHERE id = :id"), {"id": owner.hex}).one()
            draft = connection.execute(text(
                "SELECT owner_id, title, draft_revision, draft_content FROM resumes WHERE id = :id"
            ), {"id": resume.hex}).one()
        assert user == ("legacy@example.org", "")
        assert draft == (owner.hex, "Legacy draft", 2, "{}")
    finally:
        engine.dispose()


def test_readiness_states_and_liveness(tmp_path):
    settings = Settings(_env_file=None, database_url="sqlite:///" + (tmp_path / "ready.sqlite3").as_posix())
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/ready").json() == {"status": "unavailable"}
        assert client.get("/api/v1/ready").status_code == 503
        command.upgrade(migration_config(settings), "head")
        assert client.get("/api/v1/ready").status_code == 200
        engine = client.app.state.database_engine
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE resume_versions"))
        assert client.get("/api/v1/ready").status_code == 503
    bad = Settings(_env_file=None, database_url="sqlite:///" + (tmp_path / "missing" / "bad.sqlite3").as_posix())
    with TestClient(create_app(bad)) as client:
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
        assert client.get("/api/v1/health").status_code == 200


def test_database_document_roundtrip_and_validation(database):
    from pydantic import ValidationError
    _, _, factory = database
    owner, _, resume_id = seed(factory)
    document = ResumeDocument.model_validate({"skills": [{"name": "Python"}],
        "personal_information": {"full_name": "Jos\u00e9 \u674e"},
        "experience": [{"start_date": {"year": 2020}}]})
    with transaction(factory) as session:
        repo = ResumeRepository(session)
        repo.update_draft(owner, resume_id, document, 1)
        repo.create_snapshot(owner, resume_id)
        document.skills[0].name = "Changed outside repository"
    with transaction(factory) as session:
        repo = ResumeRepository(session)
        restored = repo.document(owner, resume_id)
        assert restored.skills[0].name == "Python"
        assert restored.personal_information.full_name == "Jos\u00e9 \u674e"
        assert restored.experience[0].start_date.month is None
        assert restored.skills[0].id == document.skills[0].id
        assert repo.version_document(owner, resume_id, 1) == restored
        # Corrupt JSON through trusted SQL; domain reconstruction must reject it.
        session.execute(update(Resume).where(Resume.id == resume_id).values(draft_content={"schema_version": 9}))
        with pytest.raises(ValidationError, match="Unsupported resume schema"):
            repo.document(owner, resume_id)


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
def test_invalid_resume_titles(database, title):
    from pydantic import ValidationError
    _, _, factory = database
    owner, _, _ = seed(factory)
    with pytest.raises(ValidationError), transaction(factory) as session:
        ResumeRepository(session).create(owner, title, ResumeDocument())


@pytest.mark.parametrize("echo", [False, True])
def test_database_logging_hides_private_values(tmp_path, caplog, echo):
    import logging
    settings = Settings(_env_file=None, database_url="sqlite:///" + (tmp_path / "logs.sqlite3").as_posix(), database_echo=echo)
    engine = build_engine(settings)
    secret = "synthetic-private-document-value"
    try:
        with caplog.at_level(logging.DEBUG), engine.connect() as connection:
            assert connection.execute(text("SELECT :private_value"), {"private_value": secret}).scalar() == secret
        assert secret not in caplog.text
    finally:
        engine.dispose()


def test_version_requires_existing_resume(database):
    _, _, factory = database
    with pytest.raises(IntegrityError), transaction(factory) as session:
        session.add(ResumeVersion(resume_id=uuid4(), version_number=1, source_draft_revision=1,
                                  schema_version=1, content=ResumeDocument().model_dump(mode="json")))
        session.flush()


def test_naive_timestamp_is_rejected(database):
    from datetime import datetime
    from sqlalchemy.exc import StatementError
    _, _, factory = database
    owner, _, _ = seed(factory)
    with pytest.raises(StatementError, match="Timestamp must have a timezone"), transaction(factory) as session:
        session.execute(update(User).where(User.id == owner).values(updated_at=datetime(2024, 1, 1)))
