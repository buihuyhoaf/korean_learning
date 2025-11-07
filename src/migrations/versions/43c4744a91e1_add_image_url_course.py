"""add image url course

Revision ID: 43c4744a91e1
Revises: 7e6ab4b986c2
Create Date: 2025-11-03 12:27:01.302081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '43c4744a91e1'
down_revision: Union[str, None] = '7e6ab4b986c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'courses' in table_names:
        columns = {col['name'] for col in inspector.get_columns('courses')}
        if 'image_url' not in columns:
            op.add_column('courses', sa.Column('image_url', sa.String(length=500), nullable=True))

    for table in ('rate_limit', 'tier'):
        if table in table_names:
            existing_uniques = {
                constraint['name']
                for constraint in inspector.get_unique_constraints(table)
            }
            expected_name = f"uq_{table}_id"
            if expected_name not in existing_uniques:
                op.create_unique_constraint(expected_name, table, ['id'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'tier' in table_names:
        existing_uniques = {
            constraint['name']
            for constraint in inspector.get_unique_constraints('tier')
        }
        expected_name = 'uq_tier_id'
        if expected_name in existing_uniques:
            op.drop_constraint(expected_name, 'tier', type_='unique')

    if 'rate_limit' in table_names:
        existing_uniques = {
            constraint['name']
            for constraint in inspector.get_unique_constraints('rate_limit')
        }
        expected_name = 'uq_rate_limit_id'
        if expected_name in existing_uniques:
            op.drop_constraint(expected_name, 'rate_limit', type_='unique')

    if 'courses' in table_names:
        columns = {col['name'] for col in inspector.get_columns('courses')}
        if 'image_url' in columns:
            op.drop_column('courses', 'image_url')
