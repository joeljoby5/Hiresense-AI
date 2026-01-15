"""Store bounded, owner-scoped resume exports."""

from alembic import op
import sqlalchemy as sa

revision = "0002_resume_exports"
down_revision = "0001_resume_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=True),
        sa.Column("format", sa.String(4), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resume_exports")),
        sa.ForeignKeyConstraint(["resume_id", "owner_id"], ["resumes.id", "resumes.owner_id"],
                                ondelete="CASCADE", name=op.f("fk_resume_exports_resume_id_owner_id_resumes")),
        sa.CheckConstraint("source_revision >= 1", name=op.f("ck_resume_exports_positive_source_revision")),
        sa.CheckConstraint("format IN ('pdf', 'docx', 'txt', 'json')", name=op.f("ck_resume_exports_format")),
        sa.CheckConstraint("size_bytes BETWEEN 0 AND 2097152", name=op.f("ck_resume_exports_size_limit")),
    )
    op.create_index("ix_resume_exports_owner_created", "resume_exports", ["owner_id", "created_at"])
    op.create_index("ix_resume_exports_resume_id", "resume_exports", ["resume_id"])


def downgrade() -> None:
    op.drop_table("resume_exports")
