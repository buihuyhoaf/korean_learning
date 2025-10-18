"""add current_course_id to users

Revision ID: 974eefaaa9c
Revises: 
Create Date: 2024-10-18 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '974eefaaa9c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add current_course_id column to users table
    op.add_column('users', sa.Column('current_course_id', sa.Integer(), nullable=True))
    
    # Add entry_test_score column if it doesn't exist
    try:
        op.add_column('users', sa.Column('entry_test_score', sa.Integer(), nullable=True))
    except Exception:
        # Column might already exist
        pass
    
    # Add has_completed_entry_test column if it doesn't exist
    try:
        op.add_column('users', sa.Column('has_completed_entry_test', sa.Boolean(), nullable=False, server_default='false'))
    except Exception:
        # Column might already exist
        pass
    
    # Add foreign key constraint for current_course_id
    try:
        op.create_foreign_key(
            'fk_users_current_course_id',
            'users', 'courses',
            ['current_course_id'], ['id']
        )
    except Exception:
        # Constraint might already exist
        pass


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
