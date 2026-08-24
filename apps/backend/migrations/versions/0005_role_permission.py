"""Add role_permission and seed P0 role permission mappings.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-22
"""

import uuid
from collections.abc import Sequence
from typing import cast

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_CODES: frozenset[str] = frozenset(
    {
        "research.quick.execute",
        "research.standard.execute",
        "research.deep.execute",
        "stock.fundamental.read",
        "stock.technical.read",
        "stock.market.read",
        "stock.supply_chain.read",
        "stock.risk.read",
        "file.upload",
        "file.private.read",
        "report.read",
        "report.export",
        "report.review",
        "skill.retrieval.execute",
        "skill.technical.execute",
        "skill.market.execute",
        "skill.supply_chain.execute",
        "skill.scenario.execute",
        "admin.user.manage",
        "admin.role.manage",
        "admin.audit.read",
    }
)


ROLE_PERMISSION_CODES: dict[str, frozenset[str]] = {
    "FREE_USER": frozenset(
        {
            "research.quick.execute",
            "stock.fundamental.read",
            "stock.technical.read",
            "stock.market.read",
            "stock.risk.read",
            "file.upload",
            "report.read",
        }
    ),
    "PAID_USER": frozenset(
        {
            "research.quick.execute",
            "research.standard.execute",
            "stock.fundamental.read",
            "stock.technical.read",
            "stock.market.read",
            "stock.risk.read",
            "file.upload",
            "file.private.read",
            "report.read",
            "report.export",
        }
    ),
    "ANALYST": frozenset(
        {
            "research.quick.execute",
            "research.standard.execute",
            "research.deep.execute",
            "stock.fundamental.read",
            "stock.technical.read",
            "stock.market.read",
            "stock.supply_chain.read",
            "stock.risk.read",
            "file.upload",
            "file.private.read",
            "report.read",
            "report.export",
            "skill.retrieval.execute",
            "skill.technical.execute",
            "skill.market.execute",
            "skill.supply_chain.execute",
            "skill.scenario.execute",
        }
    ),
    "REVIEWER": frozenset(
        {
            "stock.fundamental.read",
            "stock.technical.read",
            "stock.market.read",
            "stock.supply_chain.read",
            "stock.risk.read",
            "report.read",
            "report.review",
        }
    ),
    "DATA_STEWARD": frozenset(
        {
            "file.upload",
            "file.private.read",
            "report.read",
            "report.review",
            "skill.retrieval.execute",
        }
    ),
    "OPS": frozenset({"report.read", "admin.audit.read"}),
    "ADMIN": PERMISSION_CODES,
    "SERVICE": frozenset(
        {
            "skill.retrieval.execute",
            "skill.technical.execute",
            "skill.market.execute",
            "skill.supply_chain.execute",
            "skill.scenario.execute",
        }
    ),
}


def _permission_parts(code: str) -> tuple[str, str]:
    resource, action = code.rsplit(".", 1)
    return resource, action


def _insert_permission(bind: sa.Connection, code: str) -> uuid.UUID:
    permission_id = cast(
        uuid.UUID | None,
        bind.execute(
            sa.text("SELECT id FROM permission WHERE code = :code"), {"code": code}
        ).scalar_one_or_none(),
    )
    if permission_id is not None:
        return permission_id

    permission_id = uuid.uuid4()
    resource, action = _permission_parts(code)
    bind.execute(
        sa.text(
            """
            INSERT INTO permission (id, code, resource, action, description)
            VALUES (:id, :code, :resource, :action, :description)
            """
        ),
        {
            "id": permission_id,
            "code": code,
            "resource": resource,
            "action": action,
            "description": None,
        },
    )
    return permission_id


def _insert_role_permission(
    bind: sa.Connection,
    role_code: str,
    permission_code: str,
    permission_id: uuid.UUID,
) -> None:
    role_id = bind.execute(
        sa.text("SELECT id FROM role WHERE code = :code"), {"code": role_code}
    ).scalar_one_or_none()
    if role_id is None:
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO role_permission (role_id, permission_id)
            VALUES (:role_id, :permission_id)
            ON CONFLICT DO NOTHING
            """
        ),
        {"role_id": role_id, "permission_id": permission_id},
    )


def upgrade() -> None:
    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    bind = op.get_bind()
    permission_ids = {code: _insert_permission(bind, code) for code in PERMISSION_CODES}
    for role_code, codes in ROLE_PERMISSION_CODES.items():
        for code in codes:
            _insert_role_permission(bind, role_code, code, permission_ids[code])


def downgrade() -> None:
    op.drop_table("role_permission")
