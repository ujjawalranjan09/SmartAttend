"""Add users.is_verified column

Revision ID: 008
Revises: 007
Create Date: 2026-06-18

The User model declares `is_verified` (used by the login flow and registration),
but migration 001 created the `users` table without it, so every login SELECT
crashed with UndefinedColumnError. This adds the missing column.
"""
from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table (PostgreSQL)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _column_exists("users", "is_verified"):
        # Existing accounts pre-date email verification — treat them as verified.
        op.add_column(
            "users",
            sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    op.drop_column("users", "is_verified")
