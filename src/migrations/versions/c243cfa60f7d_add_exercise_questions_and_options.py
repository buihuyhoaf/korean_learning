"""add_exercise_questions_and_options

Revision ID: c243cfa60f7d
Revises: b045345f442c
Create Date: 2025-11-01 10:25:11.662659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c243cfa60f7d'
down_revision: Union[str, None] = 'b045345f442c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tạo bảng exercise_questions
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

    # Tạo bảng exercise_question_options
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

    # Tạo indexes
    op.create_index('ix_exercise_questions_exercise_id', 'exercise_questions', ['exercise_id'])
    op.create_index('ix_exercise_questions_order', 'exercise_questions', ['exercise_id', 'order_index'])
    op.create_index('ix_exercise_question_options_question_id', 'exercise_question_options', ['question_id'])
    op.create_index('ix_exercise_question_options_order', 'exercise_question_options', ['question_id', 'order_index'])


def downgrade() -> None:
    # Xóa indexes
    op.drop_index('ix_exercise_question_options_order', table_name='exercise_question_options')
    op.drop_index('ix_exercise_question_options_question_id', table_name='exercise_question_options')
    op.drop_index('ix_exercise_questions_order', table_name='exercise_questions')
    op.drop_index('ix_exercise_questions_exercise_id', table_name='exercise_questions')

    # Xóa bảng
    op.drop_table('exercise_question_options')
    op.drop_table('exercise_questions')
