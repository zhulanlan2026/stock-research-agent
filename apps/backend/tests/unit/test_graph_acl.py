from stock_research.supply_chain.graph_acl import GraphAclContext, GraphAclFilter


def test_graph_acl_filters_unauthorized_edges() -> None:
    context = GraphAclContext(allowed_nodes=frozenset({"A", "B"}))
    edges = [("A", "edge", "B"), ("A", "edge", "C")]

    result = GraphAclFilter().filter_edges(edges, context)

    assert result == [("A", "edge", "B")]


def test_graph_acl_handles_empty_edges() -> None:
    context = GraphAclContext(allowed_nodes=frozenset())

    assert GraphAclFilter().filter_edges([], context) == []
