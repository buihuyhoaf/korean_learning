"""drop entry test and leaderboard tables

Revision ID: 20250115000000
Revises: 20251114224131
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250115000000'
down_revision: Union[str, None] = '20251114224131'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop entry test tables and leaderboard table"""
    # Check if tables exist before dropping to handle case where they were already dropped
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    # Drop Entry Test related tables (in order of dependencies)
    # 1. Drop tables with foreign keys first
    if 'user_entry_test_history' in tables:
        op.drop_table('user_entry_test_history')
    
    if 'user_entry_test_results' in tables:
        op.drop_table('user_entry_test_results')
    
    if 'entry_test_question_options' in tables:
        op.drop_table('entry_test_question_options')
    
    if 'entry_test_questions' in tables:
        op.drop_table('entry_test_questions')
    
    if 'entry_test_results' in tables:
        op.drop_table('entry_test_results')
    
    # 2. Drop main entry_test table
    if 'entry_tests' in tables:
        op.drop_table('entry_tests')
    
    # Drop leaderboard table
    if 'leaderboard' in tables:
        op.drop_table('leaderboard')


def downgrade() -> None:
    """Recreate entry test tables and leaderboard table"""
    # Note: This is a simplified downgrade. In production, you may want to restore actual data.
    
    # Recreate entry_tests table
    op.create_table('entry_tests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('related_course_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['related_course_id'], ['courses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate entry_test_questions table
    op.create_table('entry_test_questions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('entry_test_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('audio_url', sa.String(length=500), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['entry_test_id'], ['entry_tests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate entry_test_question_options table
    op.create_table('entry_test_question_options',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('question_id', sa.UUID(), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['entry_test_questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate entry_test_results table
    op.create_table('entry_test_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('entry_test_id', sa.UUID(), nullable=False),
        sa.Column('min_score', sa.Float(), nullable=False),
        sa.Column('max_score', sa.Float(), nullable=False),
        sa.Column('course_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['entry_test_id'], ['entry_tests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate user_entry_test_results table
    op.create_table('user_entry_test_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('entry_test_id', sa.UUID(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('recommended_course_id', sa.UUID(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['entry_test_id'], ['entry_tests.id'], ),
        sa.ForeignKeyConstraint(['recommended_course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate user_entry_test_history table
    op.create_table('user_entry_test_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('entry_test_id', sa.UUID(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('recommended_course_id', sa.UUID(), nullable=False),
        sa.Column('taken_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['entry_test_id'], ['entry_tests.id'], ),
        sa.ForeignKeyConstraint(['recommended_course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate leaderboard table
    op.create_table('leaderboard',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('season', sa.String(length=50), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('exp', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
