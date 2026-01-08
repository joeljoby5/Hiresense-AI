from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select, update

from app.database.resume_scope import resume_scope
from app.database.session import transaction
from app.domain.resume.models import ResumeDocument
from app.initialize_owner import initialize_owner
from app.models import Resume, ResumeVersion, User
from app.repositories.errors import NotFoundError, RevisionConflictError
from app.repositories.resumes import ResumeRepository
from app.repositories.users import UserRepository
from app.services.errors import IdentityUnavailableError
from app.services.resumes import ResumeService


@pytest.fixture
def services(database):
    settings, _, factory = database
    with transaction(factory) as session:
        a = UserRepository(session).create_development_owner("owner-a@example.org", settings).id
        b = UserRepository(session).create_development_owner("owner-b@example.org", settings).id
    scope = resume_scope(factory)
    return ResumeService(scope, a), ResumeService(scope, b), factory


def test_empty_and_populated_creation_retrieval_and_listing(services):
    a, b, _ = services
    empty = a.create(" Empty ")
    document = ResumeDocument.model_validate({"skills": [{"name": "Python"}],
        "personal_information": {"full_name": "Synthetic \u674e"},
        "experience": [{"start_date": {"year": 2020}}]})
    populated = a.create("Populated", document)
    b.create("Foreign")
    assert empty.content == ResumeDocument()
    assert empty.title == "Empty" and empty.draft_revision == 1
    assert a.get(populated.id).content == document
    assert a.list(limit=1).total == 2
    assert a.list(limit=1).has_more
    assert a.list(limit=1, offset=1).has_more is False
    assert a.list(search="Populated").items[0].id == populated.id


def test_metadata_content_revision_and_no_automatic_snapshot(services):
    a, _, factory = services
    item = a.create("Original")
    edited = a.update(item.id, 1, title="New")
    assert edited.draft_revision == 2 and edited.content == item.content
    with pytest.raises(RevisionConflictError) as error:
        a.update(item.id, 1, content=ResumeDocument(professional_summary="Stale"))
    assert error.value.current_revision == 2
    replaced = a.update(item.id, 2, content=ResumeDocument(professional_summary="Replacement"))
    assert replaced.draft_revision == 3 and replaced.title == "New"
    assert a.versions(item.id).total == 0
    with transaction(factory) as session:
        session.execute(update(Resume).where(Resume.id == item.id).values(draft_content={"schema_version": 2}))
    with pytest.raises(ValidationError):
        a.get(item.id)


def test_duplicate_and_checkpoint_independence_and_lineage(services):
    a, _, _ = services
    original = a.create("x" * 200, ResumeDocument.model_validate({"skills": [{"name": "Python"}]}))
    checkpoint = a.checkpoint(original.id, 1, "First")
    copy = a.duplicate(original.id)
    assert len(copy.title) <= 200 and copy.title.endswith(" (copy)")
    assert copy.parent_resume_id == original.id and copy.id != original.id
    assert copy.content.skills[0].id == original.content.skills[0].id
    assert copy.draft_revision == 1 and a.versions(copy.id).total == 0
    a.update(copy.id, 1, content=ResumeDocument(professional_summary="Independent"))
    a.update(original.id, 1, content=ResumeDocument(professional_summary="Later"))
    assert a.get(copy.id).content.professional_summary == "Independent"
    assert a.version(original.id, checkpoint.id).content == original.content
    assert a.get(original.id).content.professional_summary == "Later"
    with pytest.raises(RevisionConflictError):
        a.checkpoint(original.id, 1)
    assert a.checkpoint(original.id, 2).version_number == 2
    with pytest.raises(NotFoundError):
        a.version(copy.id, checkpoint.id)


def test_delete_preserves_children_and_other_owners(services):
    a, b, factory = services
    parent = a.create("Parent")
    child = a.duplicate(parent.id)
    grandchild = a.duplicate(child.id)
    foreign = b.create("Foreign")
    checkpoint = a.checkpoint(parent.id, 1)
    a.checkpoint(child.id, 1)
    with pytest.raises(RevisionConflictError):
        a.delete(parent.id, 2)
    assert a.get(child.id).parent_resume_id == parent.id
    a.delete(parent.id, 1)
    with pytest.raises(NotFoundError):
        a.get(parent.id)
    assert a.get(child.id).parent_resume_id is None
    assert a.get(child.id).draft_revision == 2
    assert a.get(grandchild.id).parent_resume_id == child.id
    assert a.versions(child.id).total == 1
    assert b.get(foreign.id).title == "Foreign"
    with transaction(factory) as session:
        assert session.get(ResumeVersion, checkpoint.id) is None


def test_rollback_after_partial_writes(services, monkeypatch):
    a, _, factory = services
    parent = a.create("Parent")
    child = a.duplicate(parent.id)
    original_delete = ResumeRepository.delete

    def fail_delete(*args, **kwargs):
        original_delete(*args, **kwargs)
        raise RuntimeError("Synthetic failure")

    with monkeypatch.context() as patch:
        patch.setattr(ResumeRepository, "delete", fail_delete)
        with pytest.raises(RuntimeError):
            a.delete(parent.id, 1)
    assert a.get(parent.id).title == "Parent"
    assert a.get(child.id).parent_resume_id == parent.id
    assert a.get(child.id).draft_revision == 1

    original_snapshot = ResumeRepository.create_snapshot

    def fail_snapshot(*args, **kwargs):
        original_snapshot(*args, **kwargs)
        raise RuntimeError("Synthetic failure")

    with monkeypatch.context() as patch:
        patch.setattr(ResumeRepository, "create_snapshot", fail_snapshot)
        with pytest.raises(RuntimeError):
            a.checkpoint(parent.id, 1)
    assert a.versions(parent.id).total == 0
    assert a.checkpoint(parent.id, 1).version_number == 1

    original_create = ResumeRepository.create

    def fail_create(*args, **kwargs):
        original_create(*args, **kwargs)
        raise RuntimeError("Synthetic failure")

    with monkeypatch.context() as patch:
        patch.setattr(ResumeRepository, "create", fail_create)
        with pytest.raises(RuntimeError):
            a.duplicate(parent.id)
    assert a.list().total == 2


def test_missing_inactive_and_unavailable_ownership(services):
    a, _, factory = services
    with pytest.raises(IdentityUnavailableError):
        ResumeService(a.scope, None)
    with pytest.raises(IdentityUnavailableError):
        ResumeService(a.scope, uuid4()).create("Unavailable")
    with transaction(factory) as session:
        session.execute(update(User).where(User.id == a.owner_id).values(is_active=False))
    with pytest.raises(IdentityUnavailableError):
        a.create("Inactive")


def test_service_concurrent_revision_and_checkpoint_writers(services):
    a, _, _ = services
    item = a.create("Concurrent")
    barrier = Barrier(2)

    def edit(index):
        barrier.wait(timeout=10)
        try:
            return a.update(item.id, 1, title=f"Client {index}").draft_revision
        except RevisionConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, [1, 2]))
    assert results.count(2) == 1 and results.count("conflict") == 1
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: a.checkpoint(item.id, 2).version_number, [1, 2])) == [1, 2]


def test_bootstrap_is_explicit_idempotent_and_restricted(database):
    settings, _, factory = database
    with pytest.raises(ValueError):
        initialize_owner(settings)
    settings.development_identity_enabled = True
    owner_id = initialize_owner(settings)
    assert initialize_owner(settings) == owner_id
    settings.development_owner_id = owner_id
    assert initialize_owner(settings) == owner_id
    settings.development_owner_id = uuid4()
    with pytest.raises(ValueError):
        initialize_owner(settings)
    settings.environment = "production"
    with pytest.raises(ValueError):
        initialize_owner(settings)
    with transaction(factory) as session:
        assert len(list(session.scalars(select(User)))) == 1


@pytest.mark.parametrize("options", [{"limit": 0}, {"limit": 101}, {"offset": -1},
                                     {"offset": 1_000_001}, {"sort": "injection"}, {"search": "x" * 201}])
def test_service_list_options_are_bounded(services, options):
    with pytest.raises(ValueError):
        services[0].list(**options)


@pytest.mark.parametrize("revision", [None, True, 0, -1, "1"])
def test_service_requires_valid_revisions_independently_of_http(services, revision):
    a, _, _ = services
    item = a.create("Revision precondition")
    for operation in (lambda: a.update(item.id, revision, title="Changed"),
                      lambda: a.delete(item.id, revision), lambda: a.checkpoint(item.id, revision)):
        with pytest.raises(ValueError):
            operation()
    assert a.get(item.id).draft_revision == 1 and a.versions(item.id).total == 0
