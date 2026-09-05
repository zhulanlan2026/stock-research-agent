from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import httpx

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_\u4e00-\u9fff]+")


class EmbeddingClient(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class VectorIndex(Protocol):
    def add(self, vector_id: str, vector: list[float]) -> None:
        ...


class HashEmbeddingClient:
    """确定性哈希 embedding，无外部模型依赖，作为真实 embedding 的基线实现。"""

    def __init__(self, dim: int = 768) -> None:
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_embed_one(text, self.dim) for text in texts]


class RemoteEmbeddingClient:
    """OpenAI 兼容的 embedding API 客户端。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=60.0,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.post(
            "/embeddings",
            json={"model": self._model, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        return [list(item["embedding"]) for item in data["data"]]

    async def aclose(self) -> None:
        await self._client.aclose()


class EmbeddingPipeline:
    """从文本块生成向量并写入向量索引。"""

    def __init__(self, client: EmbeddingClient, index: VectorIndex) -> None:
        self._client = client
        self._index = index

    async def index_blocks(self, blocks: list[tuple[str, str]]) -> None:
        texts = [text for _, text in blocks]
        vectors = await self._client.embed(texts)
        for (block_id, _), vector in zip(blocks, vectors, strict=True):
            self._index.add(block_id, vector)


def _embed_one(text: str, dim: int) -> list[float]:
    vector = [0.0] * dim
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode()).hexdigest()
        index = int(digest[:8], 16) % dim
        sign = 1.0 if int(digest[8:16], 16) % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]
