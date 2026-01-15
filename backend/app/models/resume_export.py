from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, Integer, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, utc_now


class ResumeExport(Base):
    __tablename__ = "resume_exports"
    __table_args__ = (
        ForeignKeyConstraint(["resume_id", "owner_id"], ["resumes.id", "resumes.owner_id"], ondelete="CASCADE"),
        CheckConstraint("source_revision >= 1", name="positive_source_revision"),
        CheckConstraint("format IN ('pdf', 'docx', 'txt', 'json')", name="format"),
        CheckConstraint("size_bytes BETWEEN 0 AND 2097152", name="size_limit"),
        Index("ix_resume_exports_owner_created", "owner_id", "created_at"),
        Index("ix_resume_exports_resume_id", "resume_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid)
    resume_id: Mapped[UUID] = mapped_column(Uuid)
    source_revision: Mapped[int] = mapped_column(Integer)
    source_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    format: Mapped[str] = mapped_column(String(4))
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
