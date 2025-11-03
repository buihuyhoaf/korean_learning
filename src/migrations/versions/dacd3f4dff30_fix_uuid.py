"""fix uuid

Revision ID: dacd3f4dff30
Revises: 01b97fe2f486
Create Date: 2025-11-03 13:48:24.007596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dacd3f4dff30'
down_revision: Union[str, None] = "01b97fe2f486"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure extension for UUID
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Add temporary UUID column
    op.add_column(
        "users",
        sa.Column("current_course_id_new", sa.dialects.postgresql.UUID(as_uuid=False), nullable=True),
    )

    # We cannot deterministically map old INTEGER IDs to new UUIDs because the prior
    # migration replaced course IDs entirely. Preserve integrity by nulling values.
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

    # Swap columns
    op.execute("ALTER TABLE users DROP COLUMN current_course_id;")
    op.execute("ALTER TABLE users RENAME COLUMN current_course_id_new TO current_course_id;")

    # Recreate FK to courses(id)
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT fk_users_current_course_id FOREIGN KEY (current_course_id) REFERENCES courses(id);"
    )


def downgrade() -> None:
    # Reverse: change current_course_id back to INTEGER, values will be nulled
    op.add_column(
        "users",
        sa.Column("current_course_id_oldint", sa.Integer(), nullable=True),
    )

    op.execute("UPDATE users SET current_course_id_oldint = NULL;")

    # Drop FK on UUID column
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

    op.execute("ALTER TABLE users DROP COLUMN current_course_id;")
    op.execute("ALTER TABLE users RENAME COLUMN current_course_id_oldint TO current_course_id;")

