"""create writing_submissions table

Revision ID: 20251111120000_create_writing_submissions
Revises: 20251110124500_add_user_push_tokens
Create Date: 2025-11-11 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision = "20251111120000_create_writing_submissions"
down_revision = "20251110124500_add_user_push_tokens"
branch_labels = None
depends_on = None

writing_submission_status = sa.Enum(
    "submitted",
    "ai_graded",
    "teacher_graded",
    name="writing_submission_status",
)


def upgrade() -> None:
    """Create the writing_submissions table with basic columns."""
    # NOTE: This is a skeleton migration. Adjust indices/defaults to your needs before autogenerating migrations.
    bind = op.get_bind()
    writing_submission_status.create(bind, checkfirst=True)

    op.create_table(
        "writing_submissions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", pg.UUID(as_uuid=True), sa.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("status", writing_submission_status, nullable=False, server_default="submitted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_writing_submissions_user_id", "writing_submissions", ["user_id"])
    op.create_index("ix_writing_submissions_exercise_id", "writing_submissions", ["exercise_id"])


def downgrade() -> None:
    """Drop the writing_submissions table."""
    op.drop_index("ix_writing_submissions_exercise_id", table_name="writing_submissions")
    op.drop_index("ix_writing_submissions_user_id", table_name="writing_submissions")
    op.drop_table("writing_submissions")

    bind = op.get_bind()
    writing_submission_status.drop(bind, checkfirst=True)


