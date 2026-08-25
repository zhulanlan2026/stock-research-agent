"""Create financial_fact table.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_fact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(precision=38, scale=12), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("disclosed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("truth_status", sa.String(length=32), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "symbol",
            "metric",
            "period",
            "revision_no",
            name="uq_financial_fact_source_symbol_metric_period_revision",
        ),
    )
    op.create_index("ix_financial_fact_tenant_id", "financial_fact", ["tenant_id"])
    op.create_index("ix_financial_fact_symbol", "financial_fact", ["symbol"])
    op.create_index("ix_financial_fact_metric", "financial_fact", ["metric"])
    op.create_index("ix_financial_fact_available_at", "financial_fact", ["available_at"])


def downgrade() -> None:
    op.drop_table("financial_fact")
