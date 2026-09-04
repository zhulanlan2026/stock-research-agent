import uuid

import pytest

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
