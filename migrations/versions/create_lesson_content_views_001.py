"""Create views for lesson content and unit tests

Revision ID: create_lesson_content_views_001
Revises: restructure_course_content_001
Create Date: 2024-01-01 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'create_lesson_content_views_001'
down_revision = 'restructure_course_content_001'
branch_labels = None
depends_on = None


def upgrade():
    """Create views for easier querying of lesson content."""
    
    # Create view for lesson content
    op.execute("""
        CREATE OR REPLACE VIEW lesson_content AS
        SELECT 
            l.id as lesson_id,
            l.title as lesson_title,
            l.description as lesson_description,
            l.order_index as lesson_order,
            u.id as unit_id,
            u.title as unit_title,
            c.id as course_id,
            c.title as course_title,
            -- Practice questions
            COALESCE(
                (SELECT COUNT(*) 
                 FROM questions q 
                 WHERE q.lesson_id = l.id AND q.question_type = 'practice'), 
                0
            ) as practice_questions_count,
            -- Listening exercises
            COALESCE(
                (SELECT COUNT(*) 
                 FROM listening_exercises le 
                 WHERE le.lesson_id = l.id), 
                0
            ) as listening_exercises_count,
            -- Speaking exercises
            COALESCE(
                (SELECT COUNT(*) 
                 FROM speaking_exercises se 
                 WHERE se.lesson_id = l.id), 
                0
            ) as speaking_exercises_count,
            -- Writing exercises
            COALESCE(
                (SELECT COUNT(*) 
                 FROM writing_exercises we 
                 WHERE we.lesson_id = l.id), 
                0
            ) as writing_exercises_count,
            -- Unit test quiz
            COALESCE(
                (SELECT COUNT(*) 
                 FROM quizzes q 
                 WHERE q.unit_id = u.id AND q.type = 'unit_test'), 
                0
            ) as unit_test_quiz_count
        FROM lessons l
        JOIN units u ON l.unit_id = u.id
        JOIN courses c ON u.course_id = c.id
    """)
    
    # Create view for unit test quizzes
    op.execute("""
        CREATE OR REPLACE VIEW unit_test_quizzes AS
        SELECT 
            q.id as quiz_id,
            q.title as quiz_title,
            q.description as quiz_description,
            q.type as quiz_type,
            u.id as unit_id,
            u.title as unit_title,
            c.id as course_id,
            c.title as course_title,
            COUNT(qu.id) as questions_count
        FROM quizzes q
        JOIN units u ON q.unit_id = u.id
        JOIN courses c ON u.course_id = c.id
        LEFT JOIN questions qu ON qu.quiz_id = q.id
        WHERE q.type = 'unit_test'
        GROUP BY q.id, q.title, q.description, q.type, u.id, u.title, c.id, c.title
    """)


def downgrade():
    """Remove views."""
    op.execute("DROP VIEW IF EXISTS unit_test_quizzes")
    op.execute("DROP VIEW IF EXISTS lesson_content")
