from collections.abc import Iterable

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


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
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
    "ADMIN": frozenset(PERMISSION_CODES),
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


def permissions_for_roles(roles: Iterable[str]) -> frozenset[str]:
    result: set[str] = set()
    for role in roles:
        result.update(ROLE_PERMISSIONS.get(role, frozenset()))
    return frozenset(result)
