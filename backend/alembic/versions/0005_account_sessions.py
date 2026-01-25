"""Add server-side account sessions and the profile display name."""

from alembic import op
import sqlalchemy as sa

revision = "0005_account_sessions"
down_revision = "0004_ats_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(120), server_default="", nullable=False))
    op.create_table(
        "account_sessions",
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("token_digest", name=op.f("pk_account_sessions")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE",
                                name=op.f("fk_account_sessions_owner_id_users")),
    )
    op.create_index("ix_account_sessions_owner_expiry", "account_sessions", ["owner_id", "expires_at"])


def downgrade() -> None:
    op.drop_table("account_sessions")
    op.drop_column("users", "display_name")
