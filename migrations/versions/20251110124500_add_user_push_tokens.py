"""Create user_push_tokens table for storing FCM tokens.

Revision ID: 20251110124500_add_user_push_tokens
Revises: create_lesson_content_views_001
Create Date: 2025-11-10 12:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251110124500_add_user_push_tokens"
down_revision: Union[str, None] = "create_lesson_content_views_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the user_push_tokens table and enforce uniqueness on tokens."""

    op.create_table(
        "user_push_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_unique_constraint("uq_user_push_tokens_token", "user_push_tokens", ["token"])

    # Remove server defaults after table creation to avoid future unintended defaults.
    op.alter_column("user_push_tokens", "last_seen", server_default=None)
    op.alter_column("user_push_tokens", "is_active", server_default=None)


def downgrade() -> None:
    """Drop the user_push_tokens table."""

    op.drop_constraint("uq_user_push_tokens_token", "user_push_tokens", type_="unique")
    op.drop_table("user_push_tokens")


