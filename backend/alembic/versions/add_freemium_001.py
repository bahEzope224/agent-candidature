"""add freemium fields to users

Revision ID: add_freemium_001
Revises: 
Create Date: 2025-03-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_freemium_001'
down_revision = None  # ← remplace par le dernier revision ID de ton alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('scraping_count_today', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('scraping_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('applications_count_month', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('applications_month', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('applications_year', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('scoring_count_today', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('scoring_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'is_premium')
    op.drop_column('users', 'scraping_count_today')
    op.drop_column('users', 'scraping_date')
    op.drop_column('users', 'applications_count_month')
    op.drop_column('users', 'applications_month')
    op.drop_column('users', 'applications_year')
    op.drop_column('users', 'scoring_count_today')
    op.drop_column('users', 'scoring_date')