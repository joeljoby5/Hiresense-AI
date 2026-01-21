"""Keep versioned, reproducible ATS inputs and results."""

from alembic import op
import sqlalchemy as sa

revision = "0004_ats_analysis"
down_revision = "0003_job_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ats_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resume_revision", sa.Integer(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=True),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ats_analyses")),
        sa.ForeignKeyConstraint(["resume_id", "owner_id"], ["resumes.id", "resumes.owner_id"],
                                ondelete="CASCADE", name=op.f("fk_ats_analyses_resume_id_owner_id_resumes")),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE",
                                name=op.f("fk_ats_analyses_job_id_jobs")),
        sa.CheckConstraint("resume_revision >= 1 AND job_revision >= 1", name=op.f("ck_ats_analyses_positive_revisions")),
    )
    op.create_index("ix_ats_analyses_owner_created", "ats_analyses", ["owner_id", "created_at"])
    op.create_index("ix_ats_analyses_job_id", "ats_analyses", ["job_id"])
    op.create_index("ix_ats_analyses_resume_id", "ats_analyses", ["resume_id"])


def downgrade() -> None:
    op.drop_table("ats_analyses")
