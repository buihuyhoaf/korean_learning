"""update questions

Revision ID: 710df97710aa
Revises: 512f7e1dc89c
Create Date: 2025-11-02 04:24:39.431016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '710df97710aa'
down_revision: Union[str, None] = '512f7e1dc89c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'user_final_quiz_attempts' in table_names:
        op.drop_table('user_final_quiz_attempts')

    if 'questions' in table_names:
        fks = {fk['name'] for fk in inspector.get_foreign_keys('questions')}
        if op.f('questions_quiz_id_fkey') in fks:
            op.drop_constraint(op.f('questions_quiz_id_fkey'), 'questions', type_='foreignkey')

        question_columns = {col['name'] for col in inspector.get_columns('questions')}
        if 'quiz_id' in question_columns:
            op.drop_column('questions', 'quiz_id')

    if 'final_quizzes' in table_names:
        op.drop_table('final_quizzes')

    if 'question_options' in table_names:
        option_columns = {col['name'] for col in inspector.get_columns('question_options')}
        if 'option_media' not in option_columns:
            op.add_column('question_options', sa.Column('option_media', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        if 'sort_order' not in option_columns:
            op.add_column('question_options', sa.Column('sort_order', sa.SmallInteger(), nullable=False, server_default='0'))
            op.alter_column('question_options', 'sort_order', server_default=None)

        op.alter_column('question_options', 'option_text', existing_type=sa.TEXT(), nullable=True)

        existing_indexes = {index['name'] for index in inspector.get_indexes('question_options')}
        if op.f('ix_question_options_question_id') not in existing_indexes:
            op.create_index(op.f('ix_question_options_question_id'), 'question_options', ['question_id'], unique=False)

        existing_fks = inspector.get_foreign_keys('question_options')
        fk_names = {fk['name'] for fk in existing_fks}
        for fk in existing_fks:
            if fk['referred_table'] == 'questions':
                op.drop_constraint(fk['name'], 'question_options', type_='foreignkey')
        if not any(fk['referred_table'] == 'questions' for fk in inspector.get_foreign_keys('question_options')):
            op.create_foreign_key(None, 'question_options', 'questions', ['question_id'], ['id'], ondelete='CASCADE')

        if 'created_at' in option_columns:
            op.drop_column('question_options', 'created_at')

    if 'question_types' in table_names:
        type_columns = {col['name'] for col in inspector.get_columns('question_types')}
        if 'code' not in type_columns:
            op.add_column('question_types', sa.Column('code', sa.String(length=50), nullable=False))
        if 'created_at' not in type_columns:
            op.add_column('question_types', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")))
            op.alter_column('question_types', 'created_at', server_default=None)

        op.alter_column('question_types', 'description', existing_type=sa.TEXT(), nullable=True)

        existing_indexes = {index['name'] for index in inspector.get_indexes('question_types')}
        if op.f('ix_question_types_code') not in existing_indexes:
            op.create_index(op.f('ix_question_types_code'), 'question_types', ['code'], unique=True)

    if 'questions' in table_names:
        question_columns = {col['name'] for col in inspector.get_columns('questions')}
        if 'media' not in question_columns:
            op.add_column('questions', sa.Column('media', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        if 'question_metadata' not in question_columns:
            op.add_column('questions', sa.Column('question_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

        op.alter_column('questions', 'content', existing_type=sa.TEXT(), nullable=True)
        op.alter_column('questions', 'explanation', existing_type=sa.TEXT(), nullable=True)

        existing_indexes = {index['name'] for index in inspector.get_indexes('questions')}
        if op.f('ix_questions_lesson_id') not in existing_indexes:
            op.create_index(op.f('ix_questions_lesson_id'), 'questions', ['lesson_id'], unique=False)
        if op.f('ix_questions_question_type_id') not in existing_indexes:
            op.create_index(op.f('ix_questions_question_type_id'), 'questions', ['question_type_id'], unique=False)

        for column_name in ('audio_url', 'correct_answer', 'question_type', 'image_url'):
            if column_name in question_columns:
                op.drop_column('questions', column_name)


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('questions', sa.Column('image_url', sa.VARCHAR(length=500), autoincrement=False, nullable=True))
    op.add_column('questions', sa.Column('question_type', sa.VARCHAR(length=50), autoincrement=False, nullable=False))
    op.add_column('questions', sa.Column('correct_answer', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('questions', sa.Column('audio_url', sa.VARCHAR(length=500), autoincrement=False, nullable=True))
    # Recreate final_quizzes table first
    op.create_table('final_quizzes',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('quizzes_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('type', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('order_index', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('unit_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], name='fk_final_quizzes_unit_id'),
    sa.PrimaryKeyConstraint('id', name='quizzes_pkey'),
    postgresql_ignore_search_path=False
    )
    # Now add quiz_id column and foreign key
    op.add_column('questions', sa.Column('quiz_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('questions_quiz_id_fkey'), 'questions', 'final_quizzes', ['quiz_id'], ['id'])
    op.drop_index(op.f('ix_questions_question_type_id'), table_name='questions')
    op.drop_index(op.f('ix_questions_lesson_id'), table_name='questions')
    op.alter_column('questions', 'explanation',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('questions', 'content',
               existing_type=sa.TEXT(),
               nullable=False)
    op.drop_column('questions', 'question_metadata')
    op.drop_column('questions', 'media')
    op.drop_index(op.f('ix_question_types_code'), table_name='question_types')
    op.alter_column('question_types', 'description',
               existing_type=sa.TEXT(),
               nullable=False)
    op.drop_column('question_types', 'created_at')
    op.drop_column('question_types', 'code')
    op.add_column('question_options', sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'question_options', type_='foreignkey')
    op.create_foreign_key(op.f('question_options_question_id_fkey'), 'question_options', 'questions', ['question_id'], ['id'])
    op.drop_index(op.f('ix_question_options_question_id'), table_name='question_options')
    op.alter_column('question_options', 'option_text',
               existing_type=sa.TEXT(),
               nullable=False)
    op.drop_column('question_options', 'sort_order')
    op.drop_column('question_options', 'option_media')
    # final_quizzes table already created above
    op.create_table('user_final_quiz_attempts',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('final_quiz_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('started_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('completed_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('score', sa.DOUBLE_PRECISION(precision=53), server_default=sa.text('0.0'), autoincrement=False, nullable=False),
    sa.Column('exp_earned', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['final_quiz_id'], ['final_quizzes.id'], name=op.f('user_final_quiz_attempts_final_quiz_id_fkey')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('user_final_quiz_attempts_user_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('user_final_quiz_attempts_pkey'))
    )
    op.create_index(op.f('ix_user_final_quiz_attempts_user_quiz'), 'user_final_quiz_attempts', ['user_id', 'final_quiz_id'], unique=False)
    op.create_index(op.f('ix_user_final_quiz_attempts_user_id'), 'user_final_quiz_attempts', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_final_quiz_attempts_started_at'), 'user_final_quiz_attempts', ['started_at'], unique=False)
    op.create_index(op.f('ix_user_final_quiz_attempts_final_quiz_id'), 'user_final_quiz_attempts', ['final_quiz_id'], unique=False)
    op.create_index(op.f('ix_user_final_quiz_attempts_completed_at'), 'user_final_quiz_attempts', ['completed_at'], unique=False)
    # ### end Alembic commands ###
