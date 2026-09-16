from stock_research.retrieval.graph_rag import GraphRagRetriever
from stock_research.supply_chain.neo4j_client import GraphData


def test_graph_rag_retriever_finds_relevant_edges() -> None:
    retriever = GraphRagRetriever(
        GraphData(
            nodes=["贵州茅台", "供应商A"],
            edges=[("贵州茅台", "supplies", "供应商A")],
        )
    )

    results = retriever.retrieve("贵州茅台 供应商A")

    assert len(results) == 1
    assert results[0].source == "贵州茅台"
    assert results[0].target == "供应商A"
    assert results[0].score > 0


def test_graph_rag_retriever_returns_empty_for_irrelevant_query() -> None:
    retriever = GraphRagRetriever(
        GraphData(
            nodes=["贵州茅台", "供应商A"],
            edges=[("贵州茅台", "supplies", "供应商A")],
        )
    )

    assert retriever.retrieve("银行 利率") == []
