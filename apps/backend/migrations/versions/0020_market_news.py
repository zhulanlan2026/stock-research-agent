"""Create market_news table.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_news",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_event_id", sa.String(length=200), nullable=False),
        sa.Column("headline", sa.String(length=500), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_event_id", name="uq_market_news_source_event_id"),
    )
    op.create_index("ix_market_news_symbol", "market_news", ["symbol"])
    op.create_index("ix_market_news_event_time", "market_news", ["event_time"])


def downgrade() -> None:
    op.drop_table("market_news")
