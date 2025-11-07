"""add_text_to_speak_to_exercises

Revision ID: b045345f442c
Revises: 3cdd7afec0ce
Create Date: 2025-11-01 09:50:52.334579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'b045345f442c'
down_revision: Union[str, None] = '3cdd7afec0ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'exercises' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('exercises')}
        if 'text_to_speak' not in columns:
            op.add_column('exercises', sa.Column('text_to_speak', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'exercises' in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns('exercises')}
        if 'text_to_speak' in columns:
            op.drop_column('exercises', 'text_to_speak')
