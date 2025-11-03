"""add uuid (safe swap using temp UUID columns)

Revision ID: 01b97fe2f486
Revises: 43c4744a91e1
Create Date: 2025-11-03 13:26:11.292434

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01b97fe2f486'
down_revision: Union[str, None] = '43c4744a91e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Define parent-child relationships to propagate FK values
    parent_children = {
        "users": [
            ("user_course_progress", "user_id"),
            ("user_unit_progress", "user_id"),
            ("user_lesson_progress", "user_id"),
            ("user_question_errors", "user_id"),
            ("user_answers", "user_id"),
            ("user_exp_log", "user_id"),
            ("user_badges", "user_id"),
            ("daily_goals", "user_id"),
            ("user_refresh_tokens", "user_id"),
            ("friends", "user_id"),
            ("friends", "friend_user_id"),
            ("leaderboard", "user_id"),
            ("ai_logs", "user_id"),
            ("notifications", "user_id"),
            ("user_entry_test_results", "user_id"),
            ("user_entry_test_history", "user_id"),
        ],
        "courses": [
            ("units", "course_id"),
            ("user_course_progress", "course_id"),
            ("entry_tests", "related_course_id"),
            ("user_entry_test_results", "recommended_course_id"),
            ("entry_test_results", "course_id"),
            ("user_entry_test_history", "recommended_course_id"),
        ],
        "units": [
            ("lessons", "unit_id"),
            ("user_unit_progress", "unit_id"),
        ],
        "lessons": [
            ("questions", "lesson_id"),
            ("user_lesson_progress", "lesson_id"),
            ("exercises", "lesson_id"),
        ],
        "question_types": [
            ("questions", "question_type_id"),
        ],
        "questions": [
            ("question_options", "question_id"),
            ("user_answers", "question_id"),
            ("user_question_errors", "question_id"),
            ("question_matching_pairs", "question_id"),
            ("question_sentence_order", "question_id"),
            ("question_audio_comprehension", "question_id"),
            ("question_pronunciation", "question_id"),
        ],
        "exercises": [
            ("exercise_questions", "exercise_id"),
        ],
        "exercise_questions": [
            ("exercise_question_options", "question_id"),
        ],
        "entry_tests": [
            ("entry_test_questions", "entry_test_id"),
            ("user_entry_test_results", "entry_test_id"),
            ("entry_test_results", "entry_test_id"),
            ("user_entry_test_history", "entry_test_id"),
        ],
        "entry_test_questions": [
            ("entry_test_question_options", "question_id"),
        ],
        "badges": [
            ("user_badges", "badge_id"),
        ],
        "tier": [
            ("users", "tier_id"),
            ("rate_limit", "tier_id"),
        ],
    }

    parent_order = [
        "tier",
        "users",
        "courses",
        "units",
        "lessons",
        "question_types",
        "questions",
        "exercises",
        "exercise_questions",
        "entry_tests",
        "entry_test_questions",
        "badges",
        "ai_logs",  # independent
        "notifications",  # independent
        "leaderboard",  # independent
        "rate_limit",  # independent
        "user_refresh_tokens",  # independent
        "daily_goals",  # independent
        "user_course_progress",
        "user_unit_progress",
        "user_lesson_progress",
        "user_question_errors",
        "user_exp_log",
        "user_badges",
        "user_answers",
        "entry_test_results",
        "entry_test_question_options",
        "question_options",
        "question_matching_pairs",
        "question_sentence_order",
        "question_audio_comprehension",
        "question_pronunciation",
        "user_entry_test_results",
        "user_entry_test_history",
        "units",  # already above, safe no-op if id_new exists
    ]

    # 1) Add id_new to all parent tables
    processed = set()
    for parent in parent_order:
        if parent in processed:
            continue
        op.execute(
            f"ALTER TABLE {parent} ADD COLUMN IF NOT EXISTS id_new uuid DEFAULT uuid_generate_v4();"
        )
        op.execute(
            f"UPDATE {parent} SET id_new = COALESCE(id_new, uuid_generate_v4());"
        )
        processed.add(parent)

    # 2) For each child FK, add fk_new and populate by join
    for parent, children in parent_children.items():
        for child_table, child_fk in children:
            op.execute(
                f"ALTER TABLE {child_table} ADD COLUMN IF NOT EXISTS {child_fk}_new uuid;"
            )
            op.execute(
                f"""
                UPDATE {child_table} c
                SET {child_fk}_new = p.id_new
                FROM {parent} p
                WHERE c.{child_fk} = p.id
                """
            )

    # Helpers to drop constraints
    def drop_fk_constraints(table: str, column: str) -> None:
        op.execute(
            f"""
            DO $$
            DECLARE r RECORD; BEGIN
            FOR r IN (
                SELECT conname
                FROM pg_constraint
                WHERE contype='f' AND conrelid='{table}'::regclass
                AND conkey[1] = (
                    SELECT attnum FROM pg_attribute
                    WHERE attrelid='{table}'::regclass AND attname='{column}'
                )
            ) LOOP
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', '{table}', r.conname);
            END LOOP; END$$;
            """
        )

    def drop_pk_constraint(table: str) -> None:
        op.execute(
            f"""
            DO $$
            DECLARE r RECORD; BEGIN
            SELECT conname INTO r FROM pg_constraint
            WHERE contype='p' AND conrelid='{table}'::regclass;
            IF r.conname IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I CASCADE', '{table}', r.conname);
            END IF; END$$;
            """
        )

    # 3) Swap child FKs
    for parent, children in parent_children.items():
        for child_table, child_fk in children:
            drop_fk_constraints(child_table, child_fk)
            op.execute(f"ALTER TABLE {child_table} DROP COLUMN {child_fk};")
            op.execute(f"ALTER TABLE {child_table} RENAME COLUMN {child_fk}_new TO {child_fk};")

    # 4) Swap parent PKs
    for parent in processed:
        drop_pk_constraint(parent)
        op.execute(f"ALTER TABLE {parent} DROP COLUMN id;")
        op.execute(f"ALTER TABLE {parent} RENAME COLUMN id_new TO id;")
        op.execute(f"ALTER TABLE {parent} ADD PRIMARY KEY (id);")

    # 5) Recreate foreign key constraints (minimal set; database will have pre-existing indexes)
    def add_fk(child: str, child_fk: str, parent: str, ondelete: str | None = None) -> None:
        clause = f"ALTER TABLE {child} ADD CONSTRAINT fk_{child}_{child_fk} FOREIGN KEY ({child_fk}) REFERENCES {parent}(id)"
        if ondelete:
            clause += f" ON DELETE {ondelete}"
        clause += ";"
        op.execute(clause)

    fk_specs = [
        ("units", "course_id", "courses", None),
        ("lessons", "unit_id", "units", None),
        ("questions", "question_type_id", "question_types", None),
        ("questions", "lesson_id", "lessons", None),
        ("question_options", "question_id", "questions", "CASCADE"),
        ("user_answers", "user_id", "users", "CASCADE"),
        ("user_answers", "question_id", "questions", "CASCADE"),
        ("user_question_errors", "user_id", "users", None),
        ("user_question_errors", "question_id", "questions", None),
        ("question_matching_pairs", "question_id", "questions", "CASCADE"),
        ("question_sentence_order", "question_id", "questions", "CASCADE"),
        ("question_audio_comprehension", "question_id", "questions", "CASCADE"),
        ("question_pronunciation", "question_id", "questions", "CASCADE"),
        ("exercises", "lesson_id", "lessons", None),
        ("exercise_questions", "exercise_id", "exercises", None),
        ("exercise_question_options", "question_id", "exercise_questions", None),
        ("user_course_progress", "user_id", "users", None),
        ("user_course_progress", "course_id", "courses", None),
        ("user_unit_progress", "user_id", "users", None),
        ("user_unit_progress", "unit_id", "units", None),
        ("user_lesson_progress", "user_id", "users", None),
        ("user_lesson_progress", "lesson_id", "lessons", None),
        ("user_exp_log", "user_id", "users", None),
        ("user_badges", "user_id", "users", None),
        ("user_badges", "badge_id", "badges", None),
        ("daily_goals", "user_id", "users", None),
        ("user_refresh_tokens", "user_id", "users", None),
        ("friends", "user_id", "users", None),
        ("friends", "friend_user_id", "users", None),
        ("leaderboard", "user_id", "users", None),
        ("ai_logs", "user_id", "users", None),
        ("notifications", "user_id", "users", None),
        ("entry_tests", "related_course_id", "courses", None),
        ("entry_test_questions", "entry_test_id", "entry_tests", None),
        ("entry_test_question_options", "question_id", "entry_test_questions", None),
        ("user_entry_test_results", "user_id", "users", None),
        ("user_entry_test_results", "entry_test_id", "entry_tests", None),
        ("user_entry_test_results", "recommended_course_id", "courses", None),
        ("entry_test_results", "entry_test_id", "entry_tests", None),
        ("entry_test_results", "course_id", "courses", None),
        ("user_entry_test_history", "user_id", "users", None),
        ("user_entry_test_history", "entry_test_id", "entry_tests", None),
        ("user_entry_test_history", "recommended_course_id", "courses", None),
        ("rate_limit", "tier_id", "tier", None),
        ("users", "tier_id", "tier", None),
    ]

    for child, fk_col, parent, ondelete in fk_specs:
        add_fk(child, fk_col, parent, ondelete)


def downgrade() -> None:
    # Conservative reverse: create integer ids and map new ones, constraints re-wired.
    # Note original integer values are not restored.

    # 1) Add integer id_tmp columns (identity) to all tables with id uuid
    tables = [
        'users', 'courses', 'units', 'lessons', 'question_types', 'questions',
        'question_options', 'user_answers', 'user_question_errors', 'question_matching_pairs',
        'question_sentence_order', 'question_audio_comprehension', 'question_pronunciation',
        'exercises', 'exercise_questions', 'exercise_question_options',
        'entry_tests', 'entry_test_questions', 'entry_test_question_options',
        'user_entry_test_results', 'entry_test_results', 'user_entry_test_history',
        'user_course_progress', 'user_unit_progress', 'user_lesson_progress',
        'user_exp_log', 'user_badges', 'daily_goals', 'user_refresh_tokens',
        'friends', 'leaderboard', 'ai_logs', 'notifications', 'tier', 'rate_limit'
    ]

    for t in tables:
        op.execute(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS id_tmp integer GENERATED BY DEFAULT AS IDENTITY;")
        # populate by assigning sequence-generated values (order not guaranteed)
        # values auto-filled on next step when set not null + swap

    # Parent-child map to recreate integer FKs
    parent_children = {
        'users': [('user_course_progress','user_id'),('user_unit_progress','user_id'),('user_lesson_progress','user_id'),('user_question_errors','user_id'),('user_answers','user_id'),('user_exp_log','user_id'),('user_badges','user_id'),('daily_goals','user_id'),('user_refresh_tokens','user_id'),('friends','user_id'),('friends','friend_user_id'),('leaderboard','user_id'),('ai_logs','user_id'),('notifications','user_id'),('user_entry_test_results','user_id'),('user_entry_test_history','user_id')],
        'courses': [('units','course_id'),('user_course_progress','course_id'),('entry_tests','related_course_id'),('user_entry_test_results','recommended_course_id'),('entry_test_results','course_id'),('user_entry_test_history','recommended_course_id')],
        'units': [('lessons','unit_id'),('user_unit_progress','unit_id')],
        'lessons': [('questions','lesson_id'),('user_lesson_progress','lesson_id'),('exercises','lesson_id')],
        'question_types': [('questions','question_type_id')],
        'questions': [('question_options','question_id'),('user_answers','question_id'),('user_question_errors','question_id'),('question_matching_pairs','question_id'),('question_sentence_order','question_id'),('question_audio_comprehension','question_id'),('question_pronunciation','question_id')],
        'exercises': [('exercise_questions','exercise_id')],
        'exercise_questions': [('exercise_question_options','question_id')],
        'entry_tests': [('entry_test_questions','entry_test_id'),('user_entry_test_results','entry_test_id'),('entry_test_results','entry_test_id'),('user_entry_test_history','entry_test_id')],
        'entry_test_questions': [('entry_test_question_options','question_id')],
        'badges': [('user_badges','badge_id')],
        'tier': [('users','tier_id'),('rate_limit','tier_id')],
    }

    # Add fk_tmp integer columns and map via join on current uuid ids
    for parent, children in parent_children.items():
        for child_table, child_fk in children:
            op.execute(f"ALTER TABLE {child_table} ADD COLUMN IF NOT EXISTS {child_fk}_tmp integer;")
            op.execute(
                f"""
                UPDATE {child_table} c SET {child_fk}_tmp = p.id_tmp
                FROM {parent} p
                WHERE c.{child_fk} = p.id
                """
            )

    # Drop constraints helpers
    def drop_fk_constraints(table: str, column: str) -> None:
        op.execute(
            f"""
            DO $$ DECLARE r RECORD; BEGIN
            FOR r IN (
                SELECT conname FROM pg_constraint
                WHERE contype='f' AND conrelid='{table}'::regclass
                AND conkey[1] = (
                    SELECT attnum FROM pg_attribute
                    WHERE attrelid='{table}'::regclass AND attname='{column}'
                )
            ) LOOP
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', '{table}', r.conname);
            END LOOP; END$$;
            """
        )

    def drop_pk_constraint(table: str) -> None:
        op.execute(
            f"""
            DO $$ DECLARE r RECORD; BEGIN
            SELECT conname INTO r FROM pg_constraint
            WHERE contype='p' AND conrelid='{table}'::regclass;
            IF r.conname IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', '{table}', r.conname);
            END IF; END$$;
            """
        )

    # Swap child FKs back to integer
    for parent, children in parent_children.items():
        for child_table, child_fk in children:
            drop_fk_constraints(child_table, child_fk)
            op.execute(f"ALTER TABLE {child_table} DROP COLUMN {child_fk};")
            op.execute(f"ALTER TABLE {child_table} RENAME COLUMN {child_fk}_tmp TO {child_fk};")

    # Swap parent PKs to integer
    for t in tables:
        drop_pk_constraint(t)
        op.execute(f"ALTER TABLE {t} DROP COLUMN id;")
        op.execute(f"ALTER TABLE {t} RENAME COLUMN id_tmp TO id;")
        op.execute(f"ALTER TABLE {t} ADD PRIMARY KEY (id);")

    # Recreate minimal FKs (same as upgrade but now integer types)
    def add_fk(child: str, child_fk: str, parent: str, ondelete: str | None = None) -> None:
        clause = f"ALTER TABLE {child} ADD CONSTRAINT fk_{child}_{child_fk} FOREIGN KEY ({child_fk}) REFERENCES {parent}(id)"
        if ondelete:
            clause += f" ON DELETE {ondelete}"
        clause += ";"
        op.execute(clause)

    fk_specs = [
        ("units", "course_id", "courses", None),
        ("lessons", "unit_id", "units", None),
        ("questions", "question_type_id", "question_types", None),
        ("questions", "lesson_id", "lessons", None),
        ("question_options", "question_id", "questions", "CASCADE"),
        ("user_answers", "user_id", "users", "CASCADE"),
        ("user_answers", "question_id", "questions", "CASCADE"),
        ("user_question_errors", "user_id", "users", None),
        ("user_question_errors", "question_id", "questions", None),
        ("question_matching_pairs", "question_id", "questions", "CASCADE"),
        ("question_sentence_order", "question_id", "questions", "CASCADE"),
        ("question_audio_comprehension", "question_id", "questions", "CASCADE"),
        ("question_pronunciation", "question_id", "questions", "CASCADE"),
        ("exercises", "lesson_id", "lessons", None),
        ("exercise_questions", "exercise_id", "exercises", None),
        ("exercise_question_options", "question_id", "exercise_questions", None),
        ("user_course_progress", "user_id", "users", None),
        ("user_course_progress", "course_id", "courses", None),
        ("user_unit_progress", "user_id", "users", None),
        ("user_unit_progress", "unit_id", "units", None),
        ("user_lesson_progress", "user_id", "users", None),
        ("user_lesson_progress", "lesson_id", "lessons", None),
        ("user_exp_log", "user_id", "users", None),
        ("user_badges", "user_id", "users", None),
        ("user_badges", "badge_id", "badges", None),
        ("daily_goals", "user_id", "users", None),
        ("user_refresh_tokens", "user_id", "users", None),
        ("friends", "user_id", "users", None),
        ("friends", "friend_user_id", "users", None),
        ("leaderboard", "user_id", "users", None),
        ("ai_logs", "user_id", "users", None),
        ("notifications", "user_id", "users", None),
        ("entry_tests", "related_course_id", "courses", None),
        ("entry_test_questions", "entry_test_id", "entry_tests", None),
        ("entry_test_question_options", "question_id", "entry_test_questions", None),
        ("user_entry_test_results", "user_id", "users", None),
        ("user_entry_test_results", "entry_test_id", "entry_tests", None),
        ("user_entry_test_results", "recommended_course_id", "courses", None),
        ("entry_test_results", "entry_test_id", "entry_tests", None),
        ("entry_test_results", "course_id", "courses", None),
        ("user_entry_test_history", "user_id", "users", None),
        ("user_entry_test_history", "entry_test_id", "entry_tests", None),
        ("user_entry_test_history", "recommended_course_id", "courses", None),
        ("rate_limit", "tier_id", "tier", None),
        ("users", "tier_id", "tier", None),
    ]
    for child, fk_col, parent, ondelete in fk_specs:
        add_fk(child, fk_col, parent, ondelete)
