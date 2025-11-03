"""make_question_lesson_id_required

Revision ID: 7e6ab4b986c2
Revises: 2a2e7289cc15
Create Date: 2025-11-03 11:15:51.428508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e6ab4b986c2'
down_revision: Union[str, None] = '2a2e7289cc15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete any questions without lesson_id (should be none in production)
    op.execute("DELETE FROM questions WHERE lesson_id IS NULL")
    
    # Make lesson_id NOT NULL
    op.alter_column('questions', 'lesson_id',
                   existing_type=sa.Integer(),
                   nullable=False)


def downgrade() -> None:
    # Make lesson_id nullable again
    op.alter_column('questions', 'lesson_id',
                   existing_type=sa.Integer(),
                   nullable=True)
