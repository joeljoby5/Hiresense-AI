from sqlalchemy import select

from app.api.identity import resolve_owner
from app.database.session import transaction
from app.models.ats_analysis import AtsAnalysis
from test_resume_api import api
from test_resume_services import services


def test_analysis_persists_exact_revisions_and_rejects_cross_owner_access(api, database):
    client, owner, other = api
    resume = client.post("/api/v1/resumes", json={"title": "Synthetic", "content": {
        "skills": [{"name": "Python"}], "personal_information": {"email": "candidate@example.org"},
    }})
    job = client.post("/api/v1/jobs", json={"title": "Backend engineer", "company": "Example",
                                          "description": "Required: Python or Java. Preferred: PostgreSQL."})
    request = {"job_id": job.json()["id"], "resume_id": resume.json()["id"], "resume_revision": 1, "job_revision": 1}
    endpoint = "/api/v1/analyses"
    assert client.post(endpoint, json={**request, "job_revision": 2}).status_code == 409
    assert client.post(endpoint, json={**request, "resume_revision": 2}).status_code == 409
    original = client.post(endpoint, json=request)
    assert original.status_code == 201, original.text
    location = original.headers["location"]
    assert original.json()["report"]["skills"][0]["status"] == "matched"
    assert original.json()["report"]["skills"][1]["status"] == "not_evidenced"
    assert client.get(endpoint).json()[0]["id"] == original.json()["id"]
    assert "report" not in client.get(endpoint).json()[0]
    assert client.patch(resume.headers["location"], json={"expected_revision": 1, "content": {}}).status_code == 200
    assert client.patch(job.headers["location"], json={"expected_revision": 1, "archived": True}).status_code == 200
    assert client.get(location).json() == original.json()
    with transaction(database[2]) as session:
        stored = session.scalar(select(AtsAnalysis))
        assert stored.source["contact_presence"] == {"email": True, "phone": False}
        assert "personal_information" not in stored.source["resume"]
        assert stored.source["job_requirements"]["requirements"][0]["alternatives"] == ["python", "java"]
    client.app.dependency_overrides[resolve_owner] = lambda: other.owner_id
    assert client.get(endpoint).json() == []
    assert client.get(location).status_code == 404
    assert client.post(endpoint, json=request).status_code == 404
    client.app.dependency_overrides[resolve_owner] = lambda: owner.owner_id
    assert client.delete(job.headers["location"], params={"expected_revision": 2}).status_code == 204
    assert client.get(location).status_code == 404
