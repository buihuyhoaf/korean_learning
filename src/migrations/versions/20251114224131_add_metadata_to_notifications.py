"""add metadata to notifications

Revision ID: 20251114224131_add_metadata_to_notifications
Revises: ef1c46c52211
Create Date: 2025-11-14 22:41:31.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251114224131_add_metadata_to_notifications'
down_revision: Union[str, None] = '20251107105311'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add metadata column (JSON) to notifications table
    op.add_column('notifications', sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove metadata column
    op.drop_column('notifications', 'metadata')

