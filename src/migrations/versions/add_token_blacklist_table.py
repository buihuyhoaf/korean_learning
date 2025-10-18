"""add token_blacklist table

Revision ID: add_token_blacklist
Revises: 974eefaaa9c
Create Date: 2024-12-19 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_token_blacklist'
down_revision = '974eefaaa9c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create token_blacklist table
    op.create_table('token_blacklist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token', name='uq_token_blacklist_token')
    )
    
    # Create index on token column for faster lookups
    op.create_index('ix_token_blacklist_token', 'token_blacklist', ['token'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_token_blacklist_token', table_name='token_blacklist')
    
    # Drop table
    op.drop_table('token_blacklist')
