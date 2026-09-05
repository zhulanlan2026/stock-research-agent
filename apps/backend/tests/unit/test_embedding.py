import json

import httpx

from stock_research.retrieval.embedding import (
    EmbeddingPipeline,
    HashEmbeddingClient,
    RemoteEmbeddingClient,
)


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    return dot


async def test_hash_embedding_is_deterministic() -> None:
    client = HashEmbeddingClient(dim=64)

    assert await client.embed(["白酒 营收 净利润"]) == await client.embed(
        ["白酒 营收 净利润"]
    )


async def test_hash_embedding_similar_texts_are_closer() -> None:
    client = HashEmbeddingClient(dim=128)
    a = (await client.embed(["白酒 营收 净利润 增长"]))[0]
    b = (await client.embed(["白酒 营收 净利润 毛利率"]))[0]
    c = (await client.embed(["芯片 半导体 光刻机 晶圆"]))[0]

    assert _cosine(a, b) > _cosine(a, c)


async def test_embedding_pipeline_indexes_blocks() -> None:
    class _FakeIndex:
        def __init__(self) -> None:
            self.vectors: dict[str, list[float]] = {}

        def add(self, vector_id: str, vector: list[float]) -> None:
            self.vectors[vector_id] = vector

    index = _FakeIndex()
    pipeline = EmbeddingPipeline(HashEmbeddingClient(dim=64), index)

    await pipeline.index_blocks([("b1", "白酒 营收"), ("b2", "芯片 营收")])

    assert set(index.vectors) == {"b1", "b2"}


async def test_remote_embedding_client_embeds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/embeddings"
        body = json.loads(request.content)
        assert body["model"] == "text-embedding-3-small"
        assert body["input"] == ["a", "b"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [0.1, 0.2, 0.3]},
                    {"embedding": [0.4, 0.5, 0.6]},
                ]
            },
        )

    client = RemoteEmbeddingClient(
        base_url="https://example.com",
        api_key="test-key",
        model="text-embedding-3-small",
        transport=httpx.MockTransport(handler),
    )
    vectors = await client.embed(["a", "b"])
    await client.aclose()

    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
