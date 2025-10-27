"""drop lesson_content view before dropping exercises

Revision ID: 63debe8ae69d
Revises: ec2a4594bf04
Create Date: 2025-10-26 10:58:05.815918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63debe8ae69d'
down_revision: Union[str, None] = 'ec2a4594bf04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the lesson_content view first to avoid dependency issues
    op.execute("DROP VIEW IF EXISTS lesson_content CASCADE")
    
    # Also drop any other views that might depend on exercises
    op.execute("DROP VIEW IF EXISTS unit_test_quizzes CASCADE")


def downgrade() -> None:
    # Note: We cannot recreate the views without knowing their exact structure
    # This is a one-way migration to clean up dependencies
    pass
