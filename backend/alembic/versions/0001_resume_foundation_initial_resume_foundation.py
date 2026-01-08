"""Initial resume foundation

Revision ID: 0001_resume_foundation
Revises:
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_resume_foundation'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('password_hash', sa.String(length=512), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('resumes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('parent_resume_id', sa.Uuid(), nullable=True),
    sa.Column('draft_content', sa.JSON(), nullable=False),
    sa.Column('draft_revision', sa.Integer(), nullable=False),
    sa.Column('next_version_number', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('draft_revision >= 1', name=op.f('ck_resumes_positive_revision')),
    sa.CheckConstraint('length(trim(title)) BETWEEN 1 AND 200', name=op.f('ck_resumes_title_length')),
    sa.CheckConstraint('next_version_number >= 1', name=op.f('ck_resumes_positive_next_version')),
    sa.CheckConstraint('parent_resume_id IS NULL OR parent_resume_id <> id', name=op.f('ck_resumes_not_self_parent')),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_resumes_owner_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_resume_id', 'owner_id'], ['resumes.id', 'resumes.owner_id'], name=op.f('fk_resumes_parent_resume_id_owner_id_resumes'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resumes')),
    sa.UniqueConstraint('id', 'owner_id', name=op.f('uq_resumes_id_owner_id'))
    )
    with op.batch_alter_table('resumes', schema=None) as batch_op:
        batch_op.create_index('ix_resumes_owner_updated', ['owner_id', 'updated_at'], unique=False)

    op.create_table('resume_versions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('resume_id', sa.Uuid(), nullable=False),
    sa.Column('version_number', sa.Integer(), nullable=False),
    sa.Column('source_draft_revision', sa.Integer(), nullable=False),
    sa.Column('schema_version', sa.Integer(), nullable=False),
    sa.Column('content', sa.JSON(), nullable=False),
    sa.Column('change_summary', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('schema_version = 1', name=op.f('ck_resume_versions_supported_schema')),
    sa.CheckConstraint('source_draft_revision >= 1', name=op.f('ck_resume_versions_positive_source_revision')),
    sa.CheckConstraint('version_number >= 1', name=op.f('ck_resume_versions_positive_version')),
    sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], name=op.f('fk_resume_versions_resume_id_resumes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resume_versions')),
    sa.UniqueConstraint('resume_id', 'version_number', name=op.f('uq_resume_versions_resume_id_version_number'))
    )

def downgrade() -> None:
    op.drop_table('resume_versions')
    with op.batch_alter_table('resumes', schema=None) as batch_op:
        batch_op.drop_index('ix_resumes_owner_updated')

    op.drop_table('resumes')
    op.drop_table('users')
