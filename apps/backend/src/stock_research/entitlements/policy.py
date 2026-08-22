PLAN_FEATURES: dict[str, frozenset[str]] = {
    "free": frozenset({"quick_research", "public_data", "basic_files"}),
    "paid": frozenset(
        {
            "quick_research",
            "standard_research",
            "public_data",
            "private_files",
            "report_export",
        }
    ),
    "analyst": frozenset(
        {
            "quick_research",
            "standard_research",
            "deep_research",
            "public_data",
            "private_files",
            "report_export",
            "supply_chain",
        }
    ),
    "admin": frozenset(
        {
            "quick_research",
            "standard_research",
            "deep_research",
            "public_data",
            "private_files",
            "report_export",
            "supply_chain",
            "admin",
        }
    ),
}


def plan_has_feature(plan_tier: str, feature: str) -> bool:
    return feature in PLAN_FEATURES.get(plan_tier, frozenset())


def quota_available(total: int, used: int, reserved: int) -> int:
    return max(0, total - used - reserved)


def can_consume_quota(total: int, used: int, reserved: int, amount: int = 1) -> bool:
    return amount > 0 and quota_available(total, used, reserved) >= amount
