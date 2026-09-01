import time

from stock_research.retrieval.bm25 import BM25Index


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
