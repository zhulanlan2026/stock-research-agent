"""Create market_minute_state table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_minute_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("as_of_minute", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_event_id", sa.String(length=200), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "as_of_minute", name="uq_market_minute_state_symbol_minute"),
    )
    op.create_index("ix_market_minute_state_symbol", "market_minute_state", ["symbol"])
    op.create_index("ix_market_minute_state_as_of_minute", "market_minute_state", ["as_of_minute"])


def downgrade() -> None:
    op.drop_table("market_minute_state")
