"""seed_question_types

Revision ID: 2a2e7289cc15
Revises: 710df97710aa
Create Date: 2025-11-03 11:06:01.859338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '2a2e7289cc15'
down_revision: Union[str, None] = '710df97710aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'question_types' not in inspector.get_table_names():
        return

    # Ensure UUID generation is available
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Seed question types if table is empty
    op.execute("""
        INSERT INTO question_types (id, code, name, description, created_at)
        SELECT id, code, name, description, created_at
        FROM (VALUES
            (uuid_generate_v4(), 'MULTIPLE_CHOICE', 'Multiple Choice', 'Question with multiple options, one correct answer', timezone('utc', now())),
            (uuid_generate_v4(), 'MATCHING', 'Matching', 'Match items from two lists', timezone('utc', now())),
            (uuid_generate_v4(), 'SENTENCE_ORDER', 'Sentence Order', 'Arrange sentences in correct order', timezone('utc', now())),
            (uuid_generate_v4(), 'AUDIO_COMPREHENSION', 'Audio Comprehension', 'Listen to audio and answer questions', timezone('utc', now())),
            (uuid_generate_v4(), 'PRONUNCIATION', 'Pronunciation', 'Practice pronunciation', timezone('utc', now())),
            (uuid_generate_v4(), 'BLANK', 'Fill in the Blank', 'Fill in missing words', timezone('utc', now()))
        ) AS v(id, code, name, description, created_at)
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
