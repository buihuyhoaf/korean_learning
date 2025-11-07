"""add current_course_id to users

Revision ID: 974eefaaa9c
Revises: 
Create Date: 2024-10-18 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '974eefaaa9c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('users')}
    existing_fks = {fk['name'] for fk in inspector.get_foreign_keys('users')}

    # Add current_course_id column to users table if missing
    if 'current_course_id' not in existing_columns:
        op.add_column('users', sa.Column('current_course_id', sa.Integer(), nullable=True))

    # Add entry_test_score column if it doesn't exist
    if 'entry_test_score' not in existing_columns:
        op.add_column('users', sa.Column('entry_test_score', sa.Integer(), nullable=True))

    # Add has_completed_entry_test column if it doesn't exist
    if 'has_completed_entry_test' not in existing_columns:
        op.add_column('users', sa.Column('has_completed_entry_test', sa.Boolean(), nullable=False, server_default='false'))

    # Add foreign key constraint for current_course_id if missing
    if 'fk_users_current_course_id' not in existing_fks:
        op.create_foreign_key(
            'fk_users_current_course_id',
            'users', 'courses',
            ['current_course_id'], ['id']
        )


def downgrade() -> None:
    # Remove foreign key constraint first
    try:
        op.drop_constraint('fk_users_current_course_id', 'users', type_='foreignkey')
    except Exception:
        pass
    
    # Remove the columns
    try:
        op.drop_column('users', 'current_course_id')
    except Exception:
        pass
    
    try:
        op.drop_column('users', 'entry_test_score')
    except Exception:
        pass
        
    try:
        op.drop_column('users', 'has_completed_entry_test')
    except Exception:
        pass
