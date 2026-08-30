from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HitlMetrics:
    total: int
    approved: int
    needs_revision: int
    rejected: int
    approval_rate: float


class HitlMetricsService:
    """基于审核决策计算 HITL 指标。"""

    def calculate(self, decisions: list[str]) -> HitlMetrics:
        total = len(decisions)
        approved = sum(1 for decision in decisions if decision == "APPROVED")
        needs_revision = sum(
            1 for decision in decisions if decision == "NEEDS_REVISION"
        )
        rejected = sum(1 for decision in decisions if decision == "REJECTED")
        approval_rate = approved / total if total else 0.0
        return HitlMetrics(
            total=total,
            approved=approved,
            needs_revision=needs_revision,
            rejected=rejected,
            approval_rate=approval_rate,
        )
