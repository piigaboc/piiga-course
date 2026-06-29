"""create initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-28

Hand-written for determinism (no live DB at authoring time). Creates the
``users``, ``courses``, ``study_sessions`` and ``lessons`` tables plus the
``course_status`` enum.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Created explicitly so we control DROP on downgrade. ``create_type=False``
# keeps the Enum column from re-issuing CREATE TYPE.
course_status = postgresql.ENUM(
    "planned",
    "in_progress",
    "completed",
    "paused",
    name="course_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    course_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("totp_secret", sa.String(length=64), nullable=True),
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "backup_codes",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("platform", sa.String(length=120), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column(
            "status",
            course_status,
            server_default="planned",
            nullable=False,
        ),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_courses_user_id", "courses", ["user_id"])

    op.create_table(
        "study_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_study_sessions_course_id", "study_sessions", ["course_id"]
    )

    op.create_table(
        "lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "is_complete",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lessons_course_id", "lessons", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_lessons_course_id", table_name="lessons")
    op.drop_table("lessons")
    op.drop_index("ix_study_sessions_course_id", table_name="study_sessions")
    op.drop_table("study_sessions")
    op.drop_index("ix_courses_user_id", table_name="courses")
    op.drop_table("courses")
    op.drop_table("users")

    bind = op.get_bind()
    course_status.drop(bind, checkfirst=True)
