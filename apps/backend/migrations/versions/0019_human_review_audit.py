"""Add audit fields to human_review_event.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "human_review_event",
        sa.Column("reason_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "human_review_event",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("human_review_event", "duration_ms")
    op.drop_column("human_review_event", "reason_code")
