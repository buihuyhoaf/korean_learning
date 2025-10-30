"""add completed_questions_count to user_lesson_progress

Revision ID: 1369c014ecdf
Revises: b8420a7c0013
Create Date: 2025-10-30 15:05:51.979547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1369c014ecdf'
down_revision: Union[str, None] = 'b8420a7c0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
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
    op.drop_column("user_lesson_progress", "completed_questions_count")