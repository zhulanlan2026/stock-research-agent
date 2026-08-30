from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.graph_review import GraphReviewService


def test_graph_review_approves_with_evidence() -> None:
    candidate = GraphCandidate(nodes=["A", "B"], edges=[("A", "edge", "B")])

    result = GraphReviewService().review(candidate, ["evidence-1"])

    assert result.status == "APPROVED"


def test_graph_review_rejects_without_evidence() -> None:
    candidate = GraphCandidate(nodes=["A", "B"], edges=[("A", "edge", "B")])

    result = GraphReviewService().review(candidate, [])

    assert result.status == "REJECTED"
    assert "Evidence" in result.reason
