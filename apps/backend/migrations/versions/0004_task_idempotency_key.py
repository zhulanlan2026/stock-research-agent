"""Add idempotency key to task.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("task", sa.Column("idempotency_key", sa.String(length=200), nullable=True))
    op.create_unique_constraint(
        "uq_task_idempotency",
        "task",
        ["tenant_id", "user_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_task_idempotency", "task", type_="unique")
    op.drop_column("task", "idempotency_key")
