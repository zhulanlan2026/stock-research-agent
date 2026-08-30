"""Create contract and order tables.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contract",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("subject_org", sa.String(length=200), nullable=False),
        sa.Column("object_org", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(precision=38, scale=12), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contract_tenant_id", "contract", ["tenant_id"])

    op.create_table(
        "order",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("order_no", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(precision=38, scale=12), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contract.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_tenant_id", "order", ["tenant_id"])
    op.create_index("ix_order_contract_id", "order", ["contract_id"])


def downgrade() -> None:
    op.drop_table("order")
    op.drop_table("contract")
