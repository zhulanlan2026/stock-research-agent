from __future__ import annotations

from dataclasses import dataclass

from stock_research.supply_chain.claim_extraction import RuleBasedClaimExtractor
from stock_research.supply_chain.graph_candidate import GraphCandidate, GraphCandidateBuilder


@dataclass(frozen=True)
class SupplyChainSkillManifest:
    name: str
    version: str
    execution_type: str
    required_scopes: tuple[str, ...]
    external_model_allowed: bool
    side_effect: str


class SupplyChainSkill:
    """确定性供应链 Skill：文本 -> Claim -> Graph Candidate。"""

    manifest = SupplyChainSkillManifest(
        name="supply_chain",
        version="1.0.0",
        execution_type="deterministic_engine",
        required_scopes=("skill.supply_chain.execute",),
        external_model_allowed=False,
        side_effect="NONE",
    )

    def __init__(self) -> None:
        self._extractor = RuleBasedClaimExtractor()
        self._builder = GraphCandidateBuilder()

    def execute(self, text: str) -> GraphCandidate:
        claims = self._extractor.extract(text)
        return self._builder.build(claims)
