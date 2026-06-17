"""Add student_profiles table

Revision ID: 006
Revises: 003
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
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
            unique=True,
        ),
        sa.Column("interests", postgresql.JSONB, default=list, server_default="[]"),
        sa.Column("strengths", postgresql.JSONB, default=list, server_default="[]"),
        sa.Column("career_goals", postgresql.JSONB, default=list, server_default="[]"),
        sa.Column("preferred_study_style", sa.String(20), nullable=True),
        sa.Column("daily_study_hours_target", sa.Integer, default=2),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_student_profiles_user_id", "student_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_student_profiles_user_id", table_name="student_profiles")
    op.drop_table("student_profiles")