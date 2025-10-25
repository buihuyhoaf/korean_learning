# Alembic Migration Commands for Korean Learning App Database Restructure

# Step 1: Create a new migration file
alembic revision -m "restructure_course_content_support_lesson_questions_and_unit_quizzes"

# Step 2: After creating the migration file, you'll need to edit the generated file
# to include the migration script content. The file will be located at:
# migrations/versions/[timestamp]_restructure_course_content_support_lesson_questions_and_unit_quizzes.py

# Step 3: Run the migration
alembic upgrade head

# Step 4: Verify the migration
alembic current
alembic history

# If you need to rollback:
# alembic downgrade -1

# Migration Content to add to the generated migration file:
"""
def upgrade():
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
    
    # Create indexes
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

def downgrade():
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
"""
