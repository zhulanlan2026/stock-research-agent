import uuid

import pytest

from stock_research.retrieval.bm25 import BM25Index
from stock_research.retrieval.embedding import EmbeddingPipeline, HashEmbeddingClient
from stock_research.retrieval.hybrid import HybridRetrievalPipeline
from stock_research.retrieval.milvus_dense import MilvusDenseIndex


def test_milvus_dense_index_roundtrip() -> None:
    collection_name = f"test_dense_{uuid.uuid4().hex[:8]}"
    try:
        index = MilvusDenseIndex(
            uri="http://localhost:19530",
            collection_name=collection_name,
            dim=3,
        )
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Milvus unavailable: {exc}")

    index.add("a", [1.0, 0.0, 0.0])
    index.add("b", [0.0, 1.0, 0.0])

    results = index.search([1.0, 0.0, 0.0], top_k=1)

    assert results[0][0] == "a"


def test_hybrid_pipeline_uses_milvus_dense() -> None:
    collection_name = f"test_hybrid_{uuid.uuid4().hex[:8]}"
    try:
        milvus = MilvusDenseIndex(
            uri="http://localhost:19530",
            collection_name=collection_name,
            dim=3,
        )
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Milvus unavailable: {exc}")

    bm25 = BM25Index()
    bm25.add_document("a", "白酒 营收")
    bm25.add_document("b", "芯片 营收")

    milvus.add("b", [1.0, 0.0, 0.0])
    milvus.add("a", [0.0, 1.0, 0.0])

    pipeline = HybridRetrievalPipeline(bm25=bm25, dense=milvus)
    results = pipeline.retrieve("白酒 营收", [0.0, 1.0, 0.0], top_k=2)

    assert "a" in results
    assert "b" in results


def test_embedding_pipeline_writes_and_retrieves_from_milvus() -> None:
    collection_name = f"test_embedding_{uuid.uuid4().hex[:8]}"
    try:
        milvus = MilvusDenseIndex(
            uri="http://localhost:19530",
            collection_name=collection_name,
            dim=64,
        )
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Milvus unavailable: {exc}")

    client = HashEmbeddingClient(dim=64)
    pipeline = EmbeddingPipeline(client, milvus)
    pipeline.index_blocks(
        [("b1", "白酒 营收 净利润 增长"), ("b2", "芯片 半导体 光刻机")]
    )

    query_vector = client.embed(["白酒 营收"])[0]
    results = milvus.search(query_vector, top_k=1)

    assert results[0][0] == "b1"
