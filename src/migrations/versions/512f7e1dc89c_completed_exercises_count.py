"""completed_exercises_count

Revision ID: 512f7e1dc89c
Revises: 3dd9394ca212
Create Date: 2025-11-01 12:37:54.876365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '512f7e1dc89c'
down_revision: Union[str, None] = '3dd9394ca212'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'user_lesson_progress' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('user_lesson_progress')}
        if 'completed_exercises_count' not in columns:
            op.add_column(
                'user_lesson_progress',
                sa.Column('completed_exercises_count', sa.Integer(), nullable=False, server_default='0')
            )
            op.alter_column(
                'user_lesson_progress',
                'completed_exercises_count',
                server_default=None
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'user_lesson_progress' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('user_lesson_progress')}
        if 'completed_exercises_count' in columns:
            op.drop_column('user_lesson_progress', 'completed_exercises_count')
