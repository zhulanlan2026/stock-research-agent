"""Add timestamps to outbox_event and side_effect_receipt.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("outbox_event", "side_effect_receipt"):
        op.add_column(
            table,
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.add_column(
            table,
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    for table in ("outbox_event", "side_effect_receipt"):
        op.drop_column(table, "updated_at")
        op.drop_column(table, "created_at")
