from __future__ import annotations

from dataclasses import dataclass

from stock_research.supply_chain.claim_extraction import ExtractedClaim


@dataclass(frozen=True)
class GraphCandidate:
    nodes: list[str]
    edges: list[tuple[str, str, str]]


class GraphCandidateBuilder:
    """从抽取出的 Claim 生成图节点和边候选。"""

    def build(self, claims: list[ExtractedClaim]) -> GraphCandidate:
        nodes: list[str] = []
        edges: list[tuple[str, str, str]] = []
        for claim in claims:
            if claim.subject not in nodes:
                nodes.append(claim.subject)
            if claim.object not in nodes:
                nodes.append(claim.object)
            edges.append((claim.subject, claim.predicate, claim.object))
        return GraphCandidate(nodes=nodes, edges=edges)
