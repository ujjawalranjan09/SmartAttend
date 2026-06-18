"""Backfill NULL booleans on users and add proper server defaults

Revision ID: 010
Revises: 009
Create Date: 2026-06-18

Migration 001 created users.is_active and users.totp_enabled with only a
Python-side `default=` (no server_default), so legacy rows in production carry
NULL. Pydantic's UserResponse declares both as required `bool`, so any such row
caused `ValidationError: Input should be a valid boolean` -> HTTP 500 on every
endpoint returning a user (login, /students, /users/me, ...).

This migration:
  1. Backfills existing NULLs (False for is_active is conservative but safe;
     totp_enabled=False matches the model default).
  2. Sets NOT NULL + server_default so future inserts can never reintroduce NULL.
"""
from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
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
    # ── users.is_active ─────────────────────────────────────────────────
    if _column_exists("users", "is_active"):
        op.execute(sa.text("UPDATE users SET is_active = FALSE WHERE is_active IS NULL"))
        op.alter_column(
            "users", "is_active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        )

    # ── users.totp_enabled ──────────────────────────────────────────────
    if _column_exists("users", "totp_enabled"):
        op.execute(sa.text("UPDATE users SET totp_enabled = FALSE WHERE totp_enabled IS NULL"))
        op.alter_column(
            "users", "totp_enabled",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        )


def downgrade() -> None:
    # Best-effort: drop the server defaults / NOT NULL constraints only.
    if _column_exists("users", "totp_enabled"):
        op.alter_column(
            "users", "totp_enabled",
            existing_type=sa.Boolean(),
            nullable=True,
            server_default=None,
        )
    if _column_exists("users", "is_active"):
        op.alter_column(
            "users", "is_active",
            existing_type=sa.Boolean(),
            nullable=True,
            server_default=None,
        )
