"""Create feature flag tables.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_flag",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("percentage", sa.Integer(), nullable=False),
        sa.Column("kill_switch", sa.Boolean(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "environment", name="uq_feature_flag_key_environment"),
    )

    op.create_table(
        "feature_flag_rule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flag_id", sa.Uuid(), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("rule_value", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["flag_id"], ["feature_flag.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flag_id", "rule_type", "rule_value", name="uq_feature_flag_rule"),
    )
    op.create_index("ix_feature_flag_rule_flag_id", "feature_flag_rule", ["flag_id"])

    op.create_table(
        "feature_flag_exposure",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flag_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=200), nullable=True),
        sa.Column("user_id", sa.String(length=200), nullable=True),
        sa.Column("decision", sa.Boolean(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["flag_id"], ["feature_flag.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feature_flag_exposure_flag_id", "feature_flag_exposure", ["flag_id"])


def downgrade() -> None:
    op.drop_table("feature_flag_exposure")
    op.drop_table("feature_flag_rule")
    op.drop_table("feature_flag")
