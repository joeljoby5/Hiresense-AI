from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, String, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, UTCDateTime, utc_now

class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version_number"),
        CheckConstraint("version_number >= 1", name="positive_version"),
        CheckConstraint("source_draft_revision >= 1", name="positive_source_revision"),
        CheckConstraint("schema_version = 1", name="supported_schema"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    resume_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("resumes.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer)
    source_draft_revision: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON)
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

@event.listens_for(ResumeVersion, "before_update")
def prevent_snapshot_updates(mapper, connection, target):
    raise ValueError("Historical snapshots are immutable")
