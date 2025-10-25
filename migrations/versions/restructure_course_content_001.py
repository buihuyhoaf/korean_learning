"""restructure course content support lesson questions and unit quizzes

Revision ID: restructure_course_content_001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'restructure_course_content_001'
down_revision = None  # Update this to your latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database to support new course structure."""
    
    # Add lesson_id column to questions table
    op.add_column('questions', sa.Column('lesson_id', sa.Integer(), nullable=True))
    
    # Add question_type column to questions table
    op.add_column('questions', sa.Column('question_type', sa.String(50), nullable=True, default='practice'))
    
    # Add unit_id column to quizzes table
    op.add_column('quizzes', sa.Column('unit_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraints
    op.create_foreign_key('fk_questions_lesson_id', 'questions', 'lessons', ['lesson_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_quizzes_unit_id', 'quizzes', 'units', ['unit_id'], ['id'], ondelete='CASCADE')
    
    # Migrate existing quiz questions to lesson questions
    op.execute("""
        UPDATE questions 
        SET lesson_id = (
            SELECT lesson_id 
            FROM quizzes 
            WHERE quizzes.id = questions.quiz_id
        )
        WHERE quiz_id IS NOT NULL
    """)
    
    # Update question_type for migrated questions
    op.execute("""
        UPDATE questions 
        SET question_type = 'practice'
        WHERE lesson_id IS NOT NULL AND question_type = 'practice'
    """)
    
    # Create indexes for better performance
    op.create_index('idx_questions_lesson_id', 'questions', ['lesson_id'])
    op.create_index('idx_questions_question_type', 'questions', ['question_type'])
    op.create_index('idx_quizzes_unit_id', 'quizzes', ['unit_id'])
    
    # Update existing quizzes to be unit-level (final tests)
    op.execute("""
        UPDATE quizzes 
        SET unit_id = (
            SELECT unit_id 
            FROM lessons 
            WHERE lessons.id = quizzes.lesson_id
        ),
        type = 'unit_test'
        WHERE lesson_id IS NOT NULL
    """)
    
    # Add comments for documentation
    op.execute("COMMENT ON COLUMN questions.lesson_id IS 'Reference to lesson for practice questions'")
    op.execute("COMMENT ON COLUMN questions.question_type IS 'Type of question: practice, assessment, listening, speaking, writing'")
    op.execute("COMMENT ON COLUMN quizzes.unit_id IS 'Reference to unit for final unit tests'")
    op.execute("COMMENT ON COLUMN quizzes.type IS 'Type of quiz: unit_test, lesson_test, etc.'")


def downgrade():
    """Downgrade database to previous structure."""
    
    # Remove indexes
    op.drop_index('idx_quizzes_unit_id', 'quizzes')
    op.drop_index('idx_questions_question_type', 'questions')
    op.drop_index('idx_questions_lesson_id', 'questions')
    
    # Remove foreign key constraints
    op.drop_constraint('fk_quizzes_unit_id', 'quizzes', type_='foreignkey')
    op.drop_constraint('fk_questions_lesson_id', 'questions', type_='foreignkey')
    
    # Remove columns
    op.drop_column('quizzes', 'unit_id')
    op.drop_column('questions', 'question_type')
    op.drop_column('questions', 'lesson_id')
