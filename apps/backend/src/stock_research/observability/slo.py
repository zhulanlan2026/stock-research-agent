from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SloTarget:
    name: str
    limit: float
    operator: str  # "<=" 表示越小越好，">=" 表示越大越好


DEFAULT_SLO_TARGETS: tuple[SloTarget, ...] = (
    SloTarget("availability", 0.999, ">="),
    SloTarget("normal_api_p95_ms", 500.0, "<="),
    SloTarget("login_auth_p95_ms", 300.0, "<="),
    SloTarget("quick_research_p95_s", 20.0, "<="),
    SloTarget("standard_research_p95_s", 90.0, "<="),
    SloTarget("standard_retrieval_p95_s", 1.5, "<="),
    SloTarget("major_risk_retrieval_p95_s", 2.0, "<="),
    SloTarget("cross_tenant_unauthorized_recall", 0.0, "<="),
    SloTarget("duplicate_visible_side_effects", 0.0, "<="),
    SloTarget("postgresql_rpo_min", 15.0, "<="),
    SloTarget("postgresql_rto_h", 4.0, "<="),
)


class SloEvaluator:
    """按 spec §40 的 SLO 目标判断观测值是否达标。"""

    def __init__(self, targets: Iterable[SloTarget] | None = None) -> None:
        self._targets = {target.name: target for target in (targets or DEFAULT_SLO_TARGETS)}

    def is_compliant(self, name: str, value: float) -> bool:
        target = self._targets.get(name)
        if target is None:
            return True
        if target.operator == "<=":
            return value <= target.limit
        return value >= target.limit

    def evaluate(self, observations: dict[str, float]) -> dict[str, bool]:
        return {
            name: self.is_compliant(name, value)
            for name, value in observations.items()
        }

    def all_compliant(self, observations: dict[str, float]) -> bool:
        return all(self.evaluate(observations).values())
