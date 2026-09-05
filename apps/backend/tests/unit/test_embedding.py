from stock_research.retrieval.embedding import (
    EmbeddingPipeline,
    HashEmbeddingClient,
)


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    return dot


def test_hash_embedding_is_deterministic() -> None:
    client = HashEmbeddingClient(dim=64)

    assert client.embed(["白酒 营收 净利润"]) == client.embed(["白酒 营收 净利润"])


def test_hash_embedding_similar_texts_are_closer() -> None:
    client = HashEmbeddingClient(dim=128)
    a = client.embed(["白酒 营收 净利润 增长"])[0]
    b = client.embed(["白酒 营收 净利润 毛利率"])[0]
    c = client.embed(["芯片 半导体 光刻机 晶圆"])[0]

    assert _cosine(a, b) > _cosine(a, c)


def test_embedding_pipeline_indexes_blocks() -> None:
    class _FakeIndex:
        def __init__(self) -> None:
            self.vectors: dict[str, list[float]] = {}

        def add(self, vector_id: str, vector: list[float]) -> None:
            self.vectors[vector_id] = vector

    index = _FakeIndex()
    pipeline = EmbeddingPipeline(HashEmbeddingClient(dim=64), index)

    pipeline.index_blocks([("b1", "白酒 营收"), ("b2", "芯片 营收")])

    assert set(index.vectors) == {"b1", "b2"}
