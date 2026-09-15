from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from stock_research.stores.models.evidence import Evidence

EVIDENCE_LEVEL_WEIGHTS = {
    "E1": 1.0,
    "E2": 0.8,
    "E3": 0.6,
    "E4": 0.4,
    "E5": 0.2,
    "AI-X": 0.3,
    "AI-G": 0.1,
}


class EvidenceStrengthService:
    """根据 source_level 和 citation_ready 计算可解释的证据强度。"""

    def summarize(
        self,
        *,
        symbol: str,
        as_of: datetime,
        evidence: list[Evidence],
    ) -> dict[str, Any]:
        ready_evidence = [item for item in evidence if item.citation_ready]
        level_counts = Counter(
            item.source_level or "UNKNOWN" for item in ready_evidence
        )
        score = sum(
            EVIDENCE_LEVEL_WEIGHTS.get(item.source_level or "", 0.0)
            for item in ready_evidence
        )
        strength = round(score / len(ready_evidence), 4) if ready_evidence else 0.0

        return {
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "data_available": bool(ready_evidence),
            "evidence_count": len(evidence),
            "citation_ready_count": len(ready_evidence),
            "source_levels": dict(sorted(level_counts.items())),
            "strength": strength,
            "strength_label": self._label(strength, bool(ready_evidence)),
        }

    def _label(self, strength: float, has_ready_evidence: bool) -> str:
        if not has_ready_evidence:
            return "证据不足"
        if strength >= 0.8:
            return "强"
        if strength >= 0.6:
            return "中"
        return "弱"
