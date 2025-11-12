"""add missing teacher grading columns to writing_submissions

Revision ID: 20251112123000_add_missing_teacher_columns
Revises: 20251111120000_create_writing_submissions
Create Date: 2025-11-12 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251112123000_add_missing_teacher_columns"
down_revision = "20251111120000_create_writing_submissions"
branch_labels = None
depends_on = None


TEACHER_COLUMNS: dict[str, sa.types.TypeEngine] = {
    "teacher_spelling_score": sa.Float(),
    "teacher_grammar_score": sa.Float(),
    "teacher_structure_score": sa.Float(),
    "teacher_vocabulary_score": sa.Float(),
    "teacher_feedback": sa.Text(),
}


def _current_columns(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns("writing_submissions")}


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = _current_columns(bind)

    for column_name, column_type in TEACHER_COLUMNS.items():
        if column_name not in existing_columns:
            op.add_column(
                "writing_submissions",
                sa.Column(column_name, column_type, nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = _current_columns(bind)

    for column_name in TEACHER_COLUMNS:
        if column_name in existing_columns:
            op.drop_column("writing_submissions", column_name)

