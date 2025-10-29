"""drop user quiz and question attempts tables

Revision ID: 20251029205652
Revises: ef1c46c52211
Create Date: 2025-10-29 20:56:52.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251029205652'
down_revision: Union[str, None] = 'ef1c46c52211'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop user_question_attempts table first (it has foreign key to user_quiz_attempts)
    # Check if table exists before dropping to handle case where it was already dropped
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    if 'user_question_attempts' in tables:
        op.drop_table('user_question_attempts')
    
    # Drop user_quiz_attempts table
    if 'user_quiz_attempts' in tables:
        op.drop_table('user_quiz_attempts')


def downgrade() -> None:
    # Recreate user_quiz_attempts table
    op.create_table('user_quiz_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('exp_earned', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['final_quizzes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate user_question_attempts table
    op.create_table('user_question_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_quiz_attempt_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('user_answer', sa.String(length=1000), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['user_quiz_attempt_id'], ['user_quiz_attempts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

