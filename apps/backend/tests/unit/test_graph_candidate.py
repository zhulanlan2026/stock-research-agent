from stock_research.supply_chain.claim_extraction import ExtractedClaim
from stock_research.supply_chain.graph_candidate import GraphCandidate, GraphCandidateBuilder


def test_graph_candidate_builder_creates_nodes_and_edges() -> None:
    candidate = GraphCandidateBuilder().build(
        [
            ExtractedClaim("公司A", "signed_contract_with", "公司B", "公司A与公司B签订合同"),
        ]
    )

    assert candidate.nodes == ["公司A", "公司B"]
    assert candidate.edges == [("公司A", "signed_contract_with", "公司B")]


def test_graph_candidate_builder_handles_empty_claims() -> None:
    assert GraphCandidateBuilder().build([]) == GraphCandidate(nodes=[], edges=[])
