"""create daily_missions table

Revision ID: 20251113223917_create_daily_missions
Revises: 20251112123000_add_missing_teacher_columns
Create Date: 2025-11-13 22:39:17.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251113223917_create_daily_missions"
down_revision = "20251112123000_add_missing_teacher_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'daily_missions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mission_id', sa.String(50), nullable=False),  # "m1", "m2", "m3"
        sa.Column('type', sa.String(20), nullable=False),  # "lesson", "speaking", "listening"
        sa.Column('target', sa.Integer(), nullable=False),
        sa.Column('progress', sa.Integer(), default=0, nullable=False),
        sa.Column('is_completed', sa.Boolean(), default=False, nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'mission_id', 'date', name='unique_user_mission_date')
    )
    op.create_index('idx_daily_missions_user_date', 'daily_missions', ['user_id', 'date'])
    op.create_index('idx_daily_missions_user_type', 'daily_missions', ['user_id', 'type'])


def downgrade() -> None:
    op.drop_index('idx_daily_missions_user_type', table_name='daily_missions')
    op.drop_index('idx_daily_missions_user_date', table_name='daily_missions')
    op.drop_table('daily_missions')

