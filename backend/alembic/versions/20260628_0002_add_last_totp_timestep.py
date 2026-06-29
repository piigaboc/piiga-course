"""add last_totp_timestep to users (TOTP replay protection)

Revision ID: 0002_last_totp_timestep
Revises: 0001_initial
Create Date: 2026-06-28

Adds a nullable ``last_totp_timestep`` BigInteger column to ``users``. The login
MFA-verify path records the matched TOTP timestep here and rejects any code
whose timestep is <= the stored value, preventing replay within the valid
window.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_last_totp_timestep"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_totp_timestep", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_totp_timestep")
