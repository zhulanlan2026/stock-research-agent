"""Create risk_snapshot table.

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_snapshot",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("initial_risk", postgresql.JSONB(), nullable=False),
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("damping", sa.Float(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_snapshot_tenant_id", "risk_snapshot", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("risk_snapshot")
