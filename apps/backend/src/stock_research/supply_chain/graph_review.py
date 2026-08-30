from __future__ import annotations

from dataclasses import dataclass

from stock_research.supply_chain.graph_candidate import GraphCandidate


@dataclass(frozen=True)
class GraphReviewResult:
    status: str
    reason: str


class GraphReviewService:
    """审核图候选，未绑定 Evidence 的边不允许发布。"""

    def review(
        self,
        candidate: GraphCandidate,
        evidence_ids: list[str],
    ) -> GraphReviewResult:
        if not candidate.edges:
            return GraphReviewResult("REJECTED", "图候选没有边")
        if not evidence_ids:
            return GraphReviewResult("REJECTED", "图候选未绑定 Evidence")
        return GraphReviewResult("APPROVED", "图候选已绑定 Evidence")
