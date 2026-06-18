"""Add subjects, batches, batch_schedules + linking columns

Revision ID: 011
Revises: 010
Create Date: 2026-06-19

Adds admin/catalog support for the new "admin CRUD + subjects + batches +
weekly batch scheduling" feature:

  1. subjects          — catalog of subjects (e.g. Mathematics)
  2. batches           — groups of students (e.g. 'CSE 2025 - Sec A')
  3. batch_schedules   — recurring weekly assignment of batch + teacher +
                         subject at a particular day/time

  4. courses.subject_id        -> subjects.id  (NULL = legacy course)
  5. users.default_subject_id  -> subjects.id  (faculty default subject)
  6. users.batch_id            -> batches.id   (a student's batch)

All new FK columns are NULLABLE so existing rows (including the ones in
production) stay valid without any backfill — same principle as migration 010.
The whole migration is idempotent: every CREATE TABLE / ADD COLUMN is guarded
so it is safe to re-run.
"""
from alembic import op
import sqlalchemy as sa


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ),
        {"t": table},
    )
    return result.first() is not None


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


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :name"
        ),
        {"name": index_name},
    )
    return result.first() is not None


def upgrade() -> None:
    # ── subjects ─────────────────────────────────────────────────────────
    if not _table_exists("subjects"):
        op.create_table(
            "subjects",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                      primary_key=True),
            sa.Column("institution_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("institutions.id"), nullable=False),
            sa.Column("department_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("departments.id"), nullable=True),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        )
        op.create_index("ix_subjects_institution_id", "subjects", ["institution_id"])
        op.create_unique_constraint(
            "uq_subjects_institution_code", "subjects", ["institution_id", "code"]
        )

    # ── batches ──────────────────────────────────────────────────────────
    if not _table_exists("batches"):
        op.create_table(
            "batches",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                      primary_key=True),
            sa.Column("institution_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("institutions.id"), nullable=False),
            sa.Column("department_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("departments.id"), nullable=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("academic_year", sa.String(20), nullable=True),
            sa.Column("semester", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        )
        op.create_index("ix_batches_institution_id", "batches", ["institution_id"])
        op.create_unique_constraint(
            "uq_batches_institution_code", "batches", ["institution_id", "code"]
        )

    # ── batch_schedules ──────────────────────────────────────────────────
    if not _table_exists("batch_schedules"):
        op.create_table(
            "batch_schedules",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                      primary_key=True),
            sa.Column("institution_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("institutions.id"), nullable=False),
            sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("batches.id"), nullable=False),
            sa.Column("faculty_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("users.id"), nullable=False),
            sa.Column("subject_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("subjects.id"), nullable=False),
            sa.Column("day_of_week", sa.Integer(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("room", sa.String(100), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        )
        op.create_index("ix_batch_schedules_institution_id",
                        "batch_schedules", ["institution_id"])
        op.create_index("ix_batch_schedules_batch_id",
                        "batch_schedules", ["batch_id"])
        op.create_index("ix_batch_schedules_faculty_id",
                        "batch_schedules", ["faculty_id"])
        op.create_index("ix_batch_schedules_subject_id",
                        "batch_schedules", ["subject_id"])
        op.create_unique_constraint(
            "uq_batch_schedules_batch_day_start",
            "batch_schedules",
            ["batch_id", "day_of_week", "start_time"],
        )

    # ── linking columns ──────────────────────────────────────────────────
    if not _column_exists("courses", "subject_id"):
        op.add_column(
            "courses",
            sa.Column("subject_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("subjects.id"), nullable=True),
        )

    if not _column_exists("users", "default_subject_id"):
        op.add_column(
            "users",
            sa.Column("default_subject_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("subjects.id"), nullable=True),
        )

    if not _column_exists("users", "batch_id"):
        op.add_column(
            "users",
            sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("batches.id"), nullable=True),
        )
        if not _index_exists("ix_users_batch_id"):
            op.create_index("ix_users_batch_id", "users", ["batch_id"])


def downgrade() -> None:
    # Drop columns first (FKs depend on the new tables).
    if _column_exists("users", "batch_id"):
        op.drop_column("users", "batch_id")
    if _column_exists("users", "default_subject_id"):
        op.drop_column("users", "default_subject_id")
    if _column_exists("courses", "subject_id"):
        op.drop_column("courses", "subject_id")

    if _table_exists("batch_schedules"):
        op.drop_table("batch_schedules")
    if _table_exists("batches"):
        op.drop_table("batches")
    if _table_exists("subjects"):
        op.drop_table("subjects")
