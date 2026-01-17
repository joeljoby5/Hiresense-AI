"""Create the owner-scoped job workspace."""

from alembic import op
import sqlalchemy as sa

revision = "0003_job_workspace"
down_revision = "0002_resume_exports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_jobs_owner_id_users")),
        sa.CheckConstraint("revision >= 1", name=op.f("ck_jobs_positive_revision")),
    )
    op.create_index("ix_jobs_owner_archived_updated", "jobs", ["owner_id", "archived", "updated_at"])


def downgrade() -> None:
    op.drop_table("jobs")
