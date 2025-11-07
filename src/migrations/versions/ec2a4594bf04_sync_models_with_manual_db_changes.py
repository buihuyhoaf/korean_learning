"""sync models with manual DB changes

Revision ID: ec2a4594bf04
Revises: 2deb377ba4bb
Create Date: 2025-10-26 03:56:31.632342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ec2a4594bf04'
down_revision: Union[str, None] = '2deb377ba4bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'final_quizzes' in table_names:
        columns = {col['name'] for col in inspector.get_columns('final_quizzes')}
        if 'unit_id' in columns:
            op.alter_column('final_quizzes', 'unit_id',
                       existing_type=sa.INTEGER(),
                       nullable=False,
                       comment=None,
                       existing_comment='Reference to unit for final unit tests')
        if 'type' in columns:
            op.alter_column('final_quizzes', 'type',
                       existing_type=sa.VARCHAR(length=50),
                       comment=None,
                       existing_comment='Type of quiz: unit_test, lesson_test, etc.',
                       existing_nullable=False)

        indexes = {index['name'] for index in inspector.get_indexes('final_quizzes')}
        if op.f('idx_quizzes_unit_id') in indexes:
            op.drop_index(op.f('idx_quizzes_unit_id'), table_name='final_quizzes')

        constraints = {constraint['name'] for constraint in inspector.get_foreign_keys('final_quizzes')}
        if op.f('fk_quizzes_unit_id') in constraints:
            op.drop_constraint(op.f('fk_quizzes_unit_id'), 'final_quizzes', type_='foreignkey')

    if 'questions' in table_names:
        columns = {col['name'] for col in inspector.get_columns('questions')}
        if 'lesson_id' in columns:
            op.alter_column('questions', 'lesson_id',
                       existing_type=sa.INTEGER(),
                       comment=None,
                       existing_comment='Reference to lesson for practice questions',
                       existing_nullable=True)
        if 'quiz_id' in columns:
            op.alter_column('questions', 'quiz_id',
                       existing_type=sa.INTEGER(),
                       nullable=True)

        indexes = {index['name'] for index in inspector.get_indexes('questions')}
        if op.f('idx_questions_lesson_id') in indexes:
            op.drop_index(op.f('idx_questions_lesson_id'), table_name='questions')
        if op.f('idx_questions_question_type') in indexes:
            op.drop_index(op.f('idx_questions_question_type'), table_name='questions')

        constraints = inspector.get_foreign_keys('questions')
        for constraint in constraints:
            if constraint['referred_table'] == 'lessons'
            and constraint['name'] == op.f('fk_questions_lesson_id'):
                op.drop_constraint(op.f('fk_questions_lesson_id'), 'questions', type_='foreignkey')
                break
        if not any(fk['referred_table'] == 'lessons' for fk in inspector.get_foreign_keys('questions')):
            op.create_foreign_key(None, 'questions', 'lessons', ['lesson_id'], ['id'])

    if 'user_question_attempts' in table_names:
        columns = {col['name'] for col in inspector.get_columns('user_question_attempts')}
        if 'lesson_id' in columns:
            constraints = inspector.get_foreign_keys('user_question_attempts')
            for constraint in constraints:
                if constraint['referred_table'] == 'lessons' and constraint['name'] == op.f('fk_user_question_attempts_lesson_id'):
                    op.drop_constraint(op.f('fk_user_question_attempts_lesson_id'), 'user_question_attempts', type_='foreignkey')
                    break
            op.drop_column('user_question_attempts', 'lesson_id')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'user_question_attempts' in table_names:
        columns = {col['name'] for col in inspector.get_columns('user_question_attempts')}
        if 'lesson_id' not in columns:
            op.add_column('user_question_attempts', sa.Column('lesson_id', sa.INTEGER(), autoincrement=False, nullable=True))
            op.create_foreign_key(op.f('fk_user_question_attempts_lesson_id'), 'user_question_attempts', 'lessons', ['lesson_id'], ['id'])

    if 'questions' in table_names:
        fks = inspector.get_foreign_keys('questions')
        for fk in fks:
            if fk['referred_table'] == 'lessons' and fk['name'] is None:
                op.drop_constraint(None, 'questions', type_='foreignkey')
                break
        existing_indexes = {index['name'] for index in inspector.get_indexes('questions')}
        if op.f('fk_questions_lesson_id') not in {fk['name'] for fk in inspector.get_foreign_keys('questions')}:
            op.create_foreign_key(op.f('fk_questions_lesson_id'), 'questions', 'lessons', ['lesson_id'], ['id'], ondelete='CASCADE')
        if op.f('idx_questions_question_type') not in existing_indexes:
            op.create_index(op.f('idx_questions_question_type'), 'questions', ['question_type'], unique=False)
        if op.f('idx_questions_lesson_id') not in existing_indexes:
            op.create_index(op.f('idx_questions_lesson_id'), 'questions', ['lesson_id'], unique=False)
        columns = {col['name'] for col in inspector.get_columns('questions')}
        if 'quiz_id' in columns:
            op.alter_column('questions', 'quiz_id', existing_type=sa.INTEGER(), nullable=False)
        if 'lesson_id' in columns:
            op.alter_column('questions', 'lesson_id', existing_type=sa.INTEGER(), comment='Reference to lesson for practice questions', existing_nullable=True)

    if 'final_quizzes' in table_names:
        constraints = {constraint['name'] for constraint in inspector.get_foreign_keys('final_quizzes')}
        if op.f('fk_quizzes_unit_id') not in constraints:
            op.create_foreign_key(op.f('fk_quizzes_unit_id'), 'final_quizzes', 'units', ['unit_id'], ['id'], ondelete='CASCADE')
        existing_indexes = {index['name'] for index in inspector.get_indexes('final_quizzes')}
        if op.f('idx_quizzes_unit_id') not in existing_indexes:
            op.create_index(op.f('idx_quizzes_unit_id'), 'final_quizzes', ['unit_id'], unique=False)
        columns = {col['name'] for col in inspector.get_columns('final_quizzes')}
        if 'type' in columns:
            op.alter_column('final_quizzes', 'type', existing_type=sa.VARCHAR(length=50), comment='Type of quiz: unit_test, lesson_test, etc.', existing_nullable=False)
        if 'unit_id' in columns:
            op.alter_column('final_quizzes', 'unit_id', existing_type=sa.INTEGER(), nullable=True, comment='Reference to unit for final unit tests')
