import time

from stock_research.retrieval.bm25 import BM25Index
from stock_research.retrieval.dense import DenseIndex
from stock_research.retrieval.hybrid import HybridRetrievalPipeline
from stock_research.retrieval.reranker import LexicalReranker, RerankCandidate


def test_bm25_throughput_baseline() -> None:
    index = BM25Index()
    for i in range(2000):
        index.add_document(
            f"doc-{i}",
            f"白酒 营收 净利润 增长 {i} 个百分点 毛利率 现金流",
        )

    queries = ["白酒 营收", "净利润 增长", "毛利率 现金流", "负债 杠杆"] * 250

    start = time.perf_counter()
    total_hits = 0
    for query in queries:
        total_hits += len(index.search(query, top_k=10))
    elapsed = time.perf_counter() - start

    assert total_hits > 0
    # Loose regression baseline: keep CI environment variance from causing flakiness.
    assert elapsed < 10.0, f"BM25 search degraded: {elapsed:.2f}s for {len(queries)} queries"


def test_hybrid_retrieval_throughput_baseline() -> None:
    bm25 = BM25Index()
    dense = DenseIndex()
    for i in range(1000):
        bm25.add_document(f"doc-{i}", f"白酒 营收 净利润 增长 {i} 个百分点")
        dense.add(f"doc-{i}", [1.0, float(i % 100) / 100, 0.5])

    pipeline = HybridRetrievalPipeline(bm25=bm25, dense=dense)

    start = time.perf_counter()
    total_hits = 0
    for _ in range(200):
        total_hits += len(
            pipeline.retrieve("白酒 营收", [1.0, 0.5, 0.5], top_k=10)
        )
    elapsed = time.perf_counter() - start

    assert total_hits > 0
    assert elapsed < 10.0, f"hybrid retrieval degraded: {elapsed:.2f}s for 200 queries"


def test_reranker_throughput_baseline() -> None:
    reranker = LexicalReranker()
    candidates = [
        RerankCandidate(
            f"doc-{i}",
            f"白酒 营收 净利润 增长 {i} 个百分点",
            authority_score=0.5,
            age_days=float(i),
        )
        for i in range(1000)
    ]

    start = time.perf_counter()
    for _ in range(200):
        reranker.rerank(candidates, "白酒 营收 净利润", top_k=10)
    elapsed = time.perf_counter() - start

    assert elapsed < 10.0, f"reranker degraded: {elapsed:.2f}s for 200 calls"
