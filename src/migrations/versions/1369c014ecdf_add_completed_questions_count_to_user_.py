"""add completed_questions_count to user_lesson_progress

Revision ID: 1369c014ecdf
Revises: b8420a7c0013
Create Date: 2025-10-30 15:05:51.979547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '1369c014ecdf'
down_revision: Union[str, None] = 'b8420a7c0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'user_lesson_progress' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('user_lesson_progress')}
        if 'completed_questions_count' not in columns:
            op.add_column(
                "user_lesson_progress",
                sa.Column("completed_questions_count", sa.Integer(), nullable=False, server_default="0"),
            )
            op.alter_column(
                "user_lesson_progress",
                "completed_questions_count",
                server_default=None,
            )

def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'user_lesson_progress' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('user_lesson_progress')}
        if 'completed_questions_count' in columns:
            op.drop_column("user_lesson_progress", "completed_questions_count")