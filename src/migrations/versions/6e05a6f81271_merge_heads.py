"""merge heads

Revision ID: 6e05a6f81271
Revises: add_picture_field_to_users, ce216575debb
Create Date: 2025-10-14 15:44:39.478124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e05a6f81271'
down_revision: Union[str, None] = ('add_picture_field_to_users', 'ce216575debb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
