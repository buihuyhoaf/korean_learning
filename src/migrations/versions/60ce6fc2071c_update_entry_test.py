"""update entry test

Revision ID: 60ce6fc2071c
Revises: 974eefaaa9c
Create Date: 2025-10-18 09:12:30.402443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '60ce6fc2071c'
down_revision: Union[str, None] = '974eefaaa9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    table_names = set(inspector.get_table_names())

    if 'token_blacklist' in table_names:
        existing_indexes = {
            index['name']
            for index in inspector.get_indexes('token_blacklist')
        }
        if 'ix_token_blacklist_token' in existing_indexes:
            op.drop_index(op.f('ix_token_blacklist_token'), table_name='token_blacklist')
        op.drop_table('token_blacklist')

    if 'rate_limit' in table_names:
        existing_uniques = {
            constraint['name']
            for constraint in inspector.get_unique_constraints('rate_limit')
        }
        if 'uq_rate_limit_id' not in existing_uniques:
            op.create_unique_constraint('uq_rate_limit_id', 'rate_limit', ['id'])

    if 'tier' in table_names:
        existing_uniques = {
            constraint['name']
            for constraint in inspector.get_unique_constraints('tier')
        }
        if 'uq_tier_id' not in existing_uniques:
            op.create_unique_constraint('uq_tier_id', 'tier', ['id'])

    if 'user_course_progress' in table_names:
        columns = {
            column['name']
            for column in inspector.get_columns('user_course_progress')
        }
        if 'started_at' not in columns:
            op.add_column(
                'user_course_progress',
                sa.Column(
                    'started_at',
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("timezone('utc', now())")
                )
            )
            # Remove server default after populating existing rows
            op.alter_column('user_course_progress', 'started_at', server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    table_names = set(inspector.get_table_names())

    if 'user_course_progress' in table_names:
        columns = {
            column['name']
            for column in inspector.get_columns('user_course_progress')
        }
        if 'started_at' in columns:
            op.drop_column('user_course_progress', 'started_at')

    if 'tier' in table_names:
        existing_uniques = {
            constraint['name']
            for constraint in inspector.get_unique_constraints('tier')
        }
        if 'uq_tier_id' in existing_uniques:
            op.drop_constraint('uq_tier_id', 'tier', type_='unique')

    if 'rate_limit' in table_names:
        existing_uniques = {
            constraint['name']
            for constraint in inspector.get_unique_constraints('rate_limit')
        }
        if 'uq_rate_limit_id' in existing_uniques:
            op.drop_constraint('uq_rate_limit_id', 'rate_limit', type_='unique')

    # Recreate token_blacklist table and index if needed
    if 'token_blacklist' not in table_names:
        op.create_table(
            'token_blacklist',
            sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column('token', sa.VARCHAR(), nullable=False),
            sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
            sa.PrimaryKeyConstraint('id', name=op.f('token_blacklist_pkey'))
        )
        op.create_index(op.f('ix_token_blacklist_token'), 'token_blacklist', ['token'], unique=True)
