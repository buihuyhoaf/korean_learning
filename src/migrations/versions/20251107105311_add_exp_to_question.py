"""add exp to question

Revision ID: 20251107105311
Revises: dacd3f4dff30
Create Date: 2025-11-07 10:53:11.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "20251107105311"
down_revision: Union[str, None] = "dacd3f4dff30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add max_exp column to lessons for per-lesson EXP configuration."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'lessons' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('lessons')}
        if 'max_exp' not in columns:
            op.add_column(
                "lessons",
                sa.Column("max_exp", sa.Integer(), nullable=False, server_default="120"),
            )
            op.alter_column("lessons", "max_exp", server_default=None)


def downgrade() -> None:
    """Revert max_exp column addition from lessons."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'lessons' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('lessons')}
        if 'max_exp' in columns:
            op.drop_column("lessons", "max_exp")


