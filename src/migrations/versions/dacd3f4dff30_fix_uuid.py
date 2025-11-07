"""fix uuid

Revision ID: dacd3f4dff30
Revises: 01b97fe2f486
Create Date: 2025-11-03 13:48:24.007596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'dacd3f4dff30'
down_revision: Union[str, None] = "01b97fe2f486"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure extension for UUID
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    bind = op.get_bind()
    inspector = inspect(bind)

    if 'users' not in inspector.get_table_names():
        return

    columns = {col['name']: col for col in inspector.get_columns('users')}

    current_column = columns.get('current_course_id')
    if current_column is not None and 'UUID' in str(current_column['type']).upper():
        # Column already migrated to UUID, nothing to do
        return

    if 'current_course_id_new' not in columns:
        op.add_column(
            "users",
            sa.Column("current_course_id_new", sa.dialects.postgresql.UUID(as_uuid=False), nullable=True),
        )

        op.execute("UPDATE users SET current_course_id_new = NULL;")

        # Drop existing FK constraints on users.current_course_id if present
        op.execute(
            """
            DO $$
            DECLARE r RECORD; BEGIN
            FOR r IN (
                SELECT conname FROM pg_constraint
                WHERE contype='f' AND conrelid='users'::regclass
                AND conkey[1] = (
                    SELECT attnum FROM pg_attribute
                    WHERE attrelid='users'::regclass AND attname='current_course_id'
                )
            ) LOOP
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', 'users', r.conname);
            END LOOP; END$$;
            """
        )

        if current_column is not None:
            op.execute("ALTER TABLE users DROP COLUMN current_course_id;")

        op.execute("ALTER TABLE users RENAME COLUMN current_course_id_new TO current_course_id;")

        op.execute(
            "ALTER TABLE users ADD CONSTRAINT fk_users_current_course_id FOREIGN KEY (current_course_id) REFERENCES courses(id);"
        )


def downgrade() -> None:
    # Reverse: change current_course_id back to INTEGER, values will be nulled
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'users' not in inspector.get_table_names():
        return

    columns = {col['name']: col for col in inspector.get_columns('users')}

    if 'current_course_id_oldint' not in columns:
        op.add_column(
            "users",
            sa.Column("current_course_id_oldint", sa.Integer(), nullable=True),
        )
        op.execute("UPDATE users SET current_course_id_oldint = NULL;")

    op.execute(
        """
        DO $$
        DECLARE r RECORD; BEGIN
        FOR r IN (
            SELECT conname FROM pg_constraint
            WHERE contype='f' AND conrelid='users'::regclass
            AND conkey[1] = (
                SELECT attnum FROM pg_attribute
                WHERE attrelid='users'::regclass AND attname='current_course_id'
            )
        ) LOOP
            EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', 'users', r.conname);
        END LOOP; END$$;
        """
    )

    if 'current_course_id' in columns:
        op.execute("ALTER TABLE users DROP COLUMN current_course_id;")

    op.execute("ALTER TABLE users RENAME COLUMN current_course_id_oldint TO current_course_id;")

