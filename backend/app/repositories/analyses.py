from uuid import UUID

from sqlalchemy import delete, select

from app.models.ats_analysis import AtsAnalysis
from app.repositories.errors import AnalysisNotFound
from app.repositories.jobs import JobRepository
from app.repositories.resumes import ResumeRepository

RETENTION = 20


class AnalysisRepository(ResumeRepository):
    def job(self, owner_id: UUID, job_id: UUID):
        return JobRepository(self.session).get(owner_id, job_id)

    def save_analysis(self, owner_id: UUID, resume_id: UUID, job_id: UUID, **payload):
        self.get(owner_id, resume_id)
        self.job(owner_id, job_id)
        row = AtsAnalysis(owner_id=owner_id, resume_id=resume_id, job_id=job_id, **payload)
        self.session.add(row)
        self.session.flush()
        older = (select(AtsAnalysis.id).where(AtsAnalysis.owner_id == owner_id)
                 .order_by(AtsAnalysis.created_at.desc(), AtsAnalysis.id.desc()).offset(RETENTION))
        self.session.execute(delete(AtsAnalysis).where(AtsAnalysis.id.in_(older)))
        return row

    def analyses(self, owner_id: UUID):
        return list(self.session.scalars(select(AtsAnalysis).where(AtsAnalysis.owner_id == owner_id)
                                         .order_by(AtsAnalysis.created_at.desc(), AtsAnalysis.id.desc()).limit(RETENTION)))

    def analysis(self, owner_id: UUID, analysis_id: UUID):
        row = self.session.scalar(select(AtsAnalysis).where(AtsAnalysis.id == analysis_id, AtsAnalysis.owner_id == owner_id))
        if row is None:
            raise AnalysisNotFound()
        return row
