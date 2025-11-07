"""add_exercise_questions_and_options

Revision ID: c243cfa60f7d
Revises: b045345f442c
Create Date: 2025-11-01 10:25:11.662659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c243cfa60f7d'
down_revision: Union[str, None] = 'b045345f442c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'exercise_questions' not in table_names:
        op.create_table(
            'exercise_questions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('exercise_id', sa.Integer(), nullable=False),
            sa.Column('question_text', sa.Text(), nullable=False),
            sa.Column('explanation', sa.Text(), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        table_names.add('exercise_questions')

    if 'exercise_question_options' not in table_names:
        op.create_table(
            'exercise_question_options',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('question_id', sa.Integer(), nullable=False),
            sa.Column('option_text', sa.Text(), nullable=False),
            sa.Column('is_correct', sa.Boolean(), nullable=True, server_default='false'),
            sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['question_id'], ['exercise_questions.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    if 'exercise_questions' in inspector.get_table_names():
        existing_indexes = {index['name'] for index in inspector.get_indexes('exercise_questions')}
        if 'ix_exercise_questions_exercise_id' not in existing_indexes:
            op.create_index('ix_exercise_questions_exercise_id', 'exercise_questions', ['exercise_id'])
        if 'ix_exercise_questions_order' not in existing_indexes:
            op.create_index('ix_exercise_questions_order', 'exercise_questions', ['exercise_id', 'order_index'])

    if 'exercise_question_options' in inspector.get_table_names():
        existing_indexes = {index['name'] for index in inspector.get_indexes('exercise_question_options')}
        if 'ix_exercise_question_options_question_id' not in existing_indexes:
            op.create_index('ix_exercise_question_options_question_id', 'exercise_question_options', ['question_id'])
        if 'ix_exercise_question_options_order' not in existing_indexes:
            op.create_index('ix_exercise_question_options_order', 'exercise_question_options', ['question_id', 'order_index'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'exercise_question_options' in inspector.get_table_names():
        existing_indexes = {index['name'] for index in inspector.get_indexes('exercise_question_options')}
        if 'ix_exercise_question_options_order' in existing_indexes:
            op.drop_index('ix_exercise_question_options_order', table_name='exercise_question_options')
        if 'ix_exercise_question_options_question_id' in existing_indexes:
            op.drop_index('ix_exercise_question_options_question_id', table_name='exercise_question_options')
        op.drop_table('exercise_question_options')

    if 'exercise_questions' in inspector.get_table_names():
        existing_indexes = {index['name'] for index in inspector.get_indexes('exercise_questions')}
        if 'ix_exercise_questions_order' in existing_indexes:
            op.drop_index('ix_exercise_questions_order', table_name='exercise_questions')
        if 'ix_exercise_questions_exercise_id' in existing_indexes:
            op.drop_index('ix_exercise_questions_exercise_id', table_name='exercise_questions')
        op.drop_table('exercise_questions')
