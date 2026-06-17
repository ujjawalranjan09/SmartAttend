"""Initial schema — all tables

Revision ID: 001
Revises: 
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("short_name", sa.String(50)),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("country", sa.String(100), default="India"),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(20)),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("institutions.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("student", "faculty", "hod", "admin", "parent", name="userrole"), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id")),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("roll_number", sa.String(50)),
        sa.Column("employee_id", sa.String(50)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("totp_secret", sa.String(64)),
        sa.Column("totp_enabled", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_institution_id", "users", ["institution_id"])

    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.id")),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("credits", sa.Integer, default=3),
        sa.Column("semester", sa.Integer),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("student_id", "course_id", name="uq_enrollment"),
    )

    op.create_table(
        "class_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id")),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("timetable_slot_id", postgresql.UUID(as_uuid=True)),
        sa.Column("scheduled_at", sa.DateTime),
        sa.Column("started_at", sa.DateTime),
        sa.Column("ended_at", sa.DateTime),
        sa.Column("status", sa.String(30), default="scheduled"),
        sa.Column("qr_token", sa.String(64)),
        sa.Column("room", sa.String(100)),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_sessions.id"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.Enum("present", "absent", "proxy_suspected", "excused", name="attendancestatus"), nullable=False),
        sa.Column("method", sa.String(50)),
        sa.Column("marked_at", sa.DateTime),
        sa.Column("geo_lat", sa.Float),
        sa.Column("geo_lon", sa.Float),
        sa.Column("geo_accuracy_m", sa.Float),
        sa.Column("device_fingerprint", sa.String(256)),
        sa.Column("wifi_bssid", sa.String(64)),
        sa.Column("face_confidence", sa.Float),
        sa.Column("proxy_score", sa.Float),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("user_agent", sa.Text),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("verification_notes", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_ar_student_id", "attendance_records", ["student_id"])
    op.create_index("ix_ar_session_id", "attendance_records", ["session_id"])

    op.create_table(
        "face_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("embedding", sa.Text, nullable=False),  # JSON-serialised float list
        sa.Column("model_version", sa.String(50)),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("attendance_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attendance_records.id")),
        sa.Column("alert_type", sa.String(60), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("resolved", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_alerts_student_id", "alerts", ["student_id"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("face_embeddings")
    op.drop_table("attendance_records")
    op.drop_table("class_sessions")
    op.drop_table("enrollments")
    op.drop_table("courses")
    op.drop_table("users")
    op.drop_table("departments")
    op.drop_table("institutions")
