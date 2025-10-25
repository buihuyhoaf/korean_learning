"""restructure_course_content_support_lesson_questions_and_unit_quizzes

Revision ID: 2deb377ba4bb
Revises: 11158b5e93e5
Create Date: 2025-10-25 15:12:16.922559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2deb377ba4bb'
down_revision: Union[str, None] = '11158b5e93e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
