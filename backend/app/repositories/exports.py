from uuid import UUID

from sqlalchemy import delete, select

from app.models.resume_export import ResumeExport
from app.repositories.errors import NotFoundError
from app.repositories.resumes import ResumeRepository

OWNER_EXPORT_LIMIT = 20


class ExportRepository(ResumeRepository):
    def save_export(self, owner_id: UUID, resume_id: UUID, revision: int, version_id: UUID | None,
                    output: str, content: bytes) -> ResumeExport:
        self.get(owner_id, resume_id)
        row = ResumeExport(owner_id=owner_id, resume_id=resume_id, source_revision=revision,
                           source_version_id=version_id, format=output, content=content, size_bytes=len(content))
        self.session.add(row)
        self.session.flush()
        # SQLite write scopes hold the writer reservation for insertion and retention.
        older = (select(ResumeExport.id).where(ResumeExport.owner_id == owner_id)
                 .order_by(ResumeExport.created_at.desc(), ResumeExport.id.desc()).offset(OWNER_EXPORT_LIMIT))
        self.session.execute(delete(ResumeExport).where(ResumeExport.id.in_(older)))
        return row

    def list_exports(self, owner_id: UUID, resume_id: UUID) -> list[ResumeExport]:
        self.get(owner_id, resume_id)
        return list(self.session.scalars(select(ResumeExport).where(
            ResumeExport.owner_id == owner_id, ResumeExport.resume_id == resume_id,
        ).order_by(ResumeExport.created_at.desc(), ResumeExport.id.desc()).limit(OWNER_EXPORT_LIMIT)))

    def get_export(self, owner_id: UUID, resume_id: UUID, export_id: UUID) -> ResumeExport:
        row = self.session.scalar(select(ResumeExport).where(
            ResumeExport.owner_id == owner_id, ResumeExport.resume_id == resume_id, ResumeExport.id == export_id,
        ))
        if row is None:
            raise NotFoundError("Export not found")
        return row
