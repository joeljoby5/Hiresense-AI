from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, utc_now


class AtsAnalysis(Base):
    __tablename__ = "ats_analyses"
    __table_args__ = (
        ForeignKeyConstraint(["resume_id", "owner_id"], ["resumes.id", "resumes.owner_id"], ondelete="CASCADE"),
        CheckConstraint("resume_revision >= 1 AND job_revision >= 1", name="positive_revisions"),
        Index("ix_ats_analyses_owner_created", "owner_id", "created_at"),
        Index("ix_ats_analyses_job_id", "job_id"),
        Index("ix_ats_analyses_resume_id", "resume_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid)
    resume_id: Mapped[UUID] = mapped_column(Uuid)
    job_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("jobs.id", ondelete="CASCADE"))
    resume_revision: Mapped[int] = mapped_column(Integer)
    resume_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    job_revision: Mapped[int] = mapped_column(Integer)
    source: Mapped[dict] = mapped_column(JSON, deferred=True)
    report: Mapped[dict] = mapped_column(JSON, deferred=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
