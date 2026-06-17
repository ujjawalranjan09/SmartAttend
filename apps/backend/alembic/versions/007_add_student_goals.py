"""Add student_goals table

Revision ID: 007
Revises: 006
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_goals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("estimated_hours", sa.Integer, nullable=True),
        sa.Column("completed_hours", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column(
            "milestones", postgresql.JSONB, default=list, server_default="[]"
        ),
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
    op.create_index(
        "ix_student_goals_student_status",
        "student_goals",
        ["student_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_goals_student_status", table_name="student_goals")
    op.drop_table("student_goals")