from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, UTCDateTime, utc_now

class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        UniqueConstraint("id", "owner_id"),
        ForeignKeyConstraint(["parent_resume_id", "owner_id"], ["resumes.id", "resumes.owner_id"], ondelete="RESTRICT"),
        CheckConstraint("parent_resume_id IS NULL OR parent_resume_id <> id", name="not_self_parent"),
        CheckConstraint("length(trim(title)) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint("draft_revision >= 1", name="positive_revision"),
        CheckConstraint("next_version_number >= 1", name="positive_next_version"),
        Index("ix_resumes_owner_updated", "owner_id", "updated_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200))
    parent_resume_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    draft_content: Mapped[dict] = mapped_column(JSON)
    draft_revision: Mapped[int] = mapped_column(Integer, default=1)
    next_version_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
