"""seed_question_types

Revision ID: 2a2e7289cc15
Revises: 710df97710aa
Create Date: 2025-11-03 11:06:01.859338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a2e7289cc15'
down_revision: Union[str, None] = '710df97710aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed question types if table is empty
    op.execute("""
        INSERT INTO question_types (code, name, description, created_at)
        SELECT code, name, description, created_at
        FROM (VALUES
            ('MULTIPLE_CHOICE', 'Multiple Choice', 'Question with multiple options, one correct answer', NOW()),
            ('MATCHING', 'Matching', 'Match items from two lists', NOW()),
            ('SENTENCE_ORDER', 'Sentence Order', 'Arrange sentences in correct order', NOW()),
            ('AUDIO_COMPREHENSION', 'Audio Comprehension', 'Listen to audio and answer questions', NOW()),
            ('PRONUNCIATION', 'Pronunciation', 'Practice pronunciation', NOW()),
            ('BLANK', 'Fill in the Blank', 'Fill in missing words', NOW())
        ) AS v(code, name, description, created_at)
        WHERE NOT EXISTS (SELECT 1 FROM question_types)
    """)


def downgrade() -> None:
    # Remove seeded question types
    op.execute("""
        DELETE FROM question_types
        WHERE code IN (
            'MULTIPLE_CHOICE', 'MATCHING', 'SENTENCE_ORDER',
            'AUDIO_COMPREHENSION', 'PRONUNCIATION', 'BLANK'
        )
    """)
