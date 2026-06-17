"""Add push_subscriptions table and performance indexes

Revision ID: 003
Revises: 002
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── push_subscriptions ────────────────────────────────────────────
    op.create_table(
        "push_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("p256dh", sa.Text, nullable=False),
        sa.Column("auth", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── performance indexes ───────────────────────────────────────────
    op.create_index(
        "idx_attendance_session_student",
        "attendance_records",
        ["session_id", "student_id"],
    )
    op.create_index(
        "idx_sessions_course_date",
        "class_sessions",
        ["course_id", "scheduled_at"],
    )
    op.execute(
        "CREATE INDEX idx_alerts_institution_unresolved "
        "ON alerts (institution_id, is_resolved) "
        "WHERE is_resolved = FALSE"
    )
    op.create_index(
        "idx_enrollments_student_course",
        "enrollments",
        ["student_id", "course_id"],
    )
    op.create_index(
        "idx_timetable_course_day",
        "timetable_slots",
        ["course_id", "day_of_week"],
    )


def downgrade() -> None:
    op.drop_index("idx_timetable_course_day", table_name="timetable_slots")
    op.drop_index("idx_enrollments_student_course", table_name="enrollments")
    op.execute("DROP INDEX IF EXISTS idx_alerts_institution_unresolved")
    op.drop_index("idx_sessions_course_date", table_name="class_sessions")
    op.drop_index("idx_attendance_session_student", table_name="attendance_records")
    op.drop_table("push_subscriptions")
