"""create weekly_leaderboard table

Revision ID: 20251114070951_create_weekly_leaderboard
Revises: 20251113223917_create_daily_missions
Create Date: 2025-11-14 07:09:51.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251114070951_create_weekly_leaderboard"
down_revision = "20251113223917_create_daily_missions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'weekly_leaderboard',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('week_start', sa.Date(), nullable=False),  # Monday of the week
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),  # None if dummy
        sa.Column('is_dummy', sa.Boolean(), nullable=False),
        sa.Column('dummy_id', sa.String(20), nullable=True),  # "dummy_1", "dummy_2", ...
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('avatar', sa.String(500), nullable=True),
        sa.Column('country', sa.String(10), nullable=True),  # Country code: "KR", "US", etc.
        sa.Column('xp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('rank_previous', sa.Integer(), nullable=True),  # Previous rank for real users
        sa.Column('xp_week_start', sa.Integer(), nullable=True),  # User's XP at week start
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('week_start', 'user_id', 'is_dummy', 'dummy_id', 
                          name='unique_weekly_entry')
    )
    op.create_index('idx_weekly_leaderboard_week_rank', 
                   'weekly_leaderboard', 
                   ['week_start', 'rank'])
    op.create_index('idx_weekly_leaderboard_user_week', 
                   'weekly_leaderboard', 
                   ['user_id', 'week_start'])
    op.create_index('idx_weekly_leaderboard_dummy_week', 
                   'weekly_leaderboard', 
                   ['dummy_id', 'week_start'])


def downgrade() -> None:
    op.drop_index('idx_weekly_leaderboard_dummy_week', table_name='weekly_leaderboard')
    op.drop_index('idx_weekly_leaderboard_user_week', table_name='weekly_leaderboard')
    op.drop_index('idx_weekly_leaderboard_week_rank', table_name='weekly_leaderboard')
    op.drop_table('weekly_leaderboard')

