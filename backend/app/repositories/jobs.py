from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.domain.jobs.models import JobDescription
from app.models.job import Job
from app.repositories.errors import JobConflict, JobNotFound


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, owner_id: UUID, job: JobDescription) -> Job:
        row = Job(owner_id=owner_id, title=job.title, company=job.company,
                  content=job.model_dump(mode="json", exclude={"title", "company"}))
        self.session.add(row)
        self.session.flush()
        return row

    def get(self, owner_id: UUID, job_id: UUID) -> Job:
        row = self.session.scalar(select(Job).where(Job.owner_id == owner_id, Job.id == job_id))
        if row is None:
            raise JobNotFound()
        return row

    def page(self, owner_id: UUID, archived: bool, search: str, sort: str, offset: int, limit: int):
        conditions = [Job.owner_id == owner_id, Job.archived == archived]
        if search:
            conditions.append(or_(Job.title.icontains(search, autoescape=True),
                                  Job.company.icontains(search, autoescape=True)))
        order = Job.title.asc() if sort == "title_asc" else Job.updated_at.desc()
        total = self.session.scalar(select(func.count()).select_from(Job).where(*conditions))
        rows = self.session.scalars(select(Job).where(*conditions).order_by(order, Job.id.asc()).offset(offset).limit(limit)).all()
        return rows, total

    def change(self, owner_id: UUID, job_id: UUID, revision: int, job: JobDescription | None, archived: bool | None) -> Job:
        changes = {"revision": Job.revision + 1, "updated_at": utc_now()}
        if job is not None:
            changes.update(title=job.title, company=job.company, content=job.model_dump(mode="json", exclude={"title", "company"}))
        if archived is not None:
            changes["archived"] = archived
        result = self.session.execute(update(Job).where(
            Job.owner_id == owner_id, Job.id == job_id, Job.revision == revision,
        ).values(**changes))
        if result.rowcount != 1:
            self._conflict(owner_id, job_id)
        return self.get(owner_id, job_id)

    def remove(self, owner_id: UUID, job_id: UUID, revision: int) -> None:
        result = self.session.execute(delete(Job).where(Job.owner_id == owner_id, Job.id == job_id, Job.revision == revision))
        if result.rowcount != 1:
            self._conflict(owner_id, job_id)

    def _conflict(self, owner_id: UUID, job_id: UUID) -> None:
        row = self.get(owner_id, job_id)
        raise JobConflict("Job listing changed", row.revision)
