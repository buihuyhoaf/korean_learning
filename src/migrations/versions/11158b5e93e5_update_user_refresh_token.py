"""update user refresh token

Revision ID: 11158b5e93e5
Revises: cff85dfb8f54
Create Date: 2025-10-19 07:58:34.197987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '11158b5e93e5'
down_revision: Union[str, None] = 'cff85dfb8f54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'token_blacklist' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('token_blacklist')}
        if 'expires_at' in columns:
            op.alter_column(
                'token_blacklist',
                'expires_at',
                existing_type=postgresql.TIMESTAMP(),
                type_=sa.DateTime(timezone=True),
                existing_nullable=False
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'token_blacklist' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('token_blacklist')}
        if 'expires_at' in columns:
            op.alter_column(
                'token_blacklist',
                'expires_at',
                existing_type=sa.DateTime(timezone=True),
                type_=postgresql.TIMESTAMP(),
                existing_nullable=False
            )
