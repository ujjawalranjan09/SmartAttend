"""Convert enum columns to VARCHAR for asyncpg compatibility

Revision ID: 009
Revises: 008
Create Date: 2026-06-18

asyncpg (the async Postgres driver) is strict-typed and refuses to implicitly
cast a string/varchar parameter into a Postgres enum column, raising
DatatypeMismatchError on every INSERT. The ORM models treat these columns as
plain strings (the Python enums subclass `str`), so the DB columns should be
VARCHAR to match. This migration converts the two enum columns created by 001
to VARCHAR. The old enum types are left in place (harmless if unreferenced).
"""
from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def _column_type(table: str, column: str) -> str:
    """Return the data_type of a column from information_schema (lowercase)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    row = result.first()
    return (row[0] if row else "").lower()


def upgrade() -> None:
    # users.role: enum 'userrole' -> varchar(20)
    if _column_type("users", "role") in ("user-defined", "enum"):
        op.alter_column(
            "users", "role",
            existing_type=sa.Enum(name="userrole"),
            type_=sa.String(20),
            existing_nullable=False,
            postgresql_using="role::text",
        )

    # attendance_records.status: enum 'attendancestatus' -> varchar(30)
    if _column_type("attendance_records", "status") in ("user-defined", "enum"):
        op.alter_column(
            "attendance_records", "status",
            existing_type=sa.Enum(name="attendancestatus"),
            type_=sa.String(30),
            existing_nullable=False,
            postgresql_using="status::text",
        )


def downgrade() -> None:
    # Best-effort: leave as varchar on downgrade (enum reconversion is lossy).
    pass
