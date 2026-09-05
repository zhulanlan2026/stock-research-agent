from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.documents.store import NormalizedBlockStore
from stock_research.retrieval.embedding import EmbeddingClient


class DenseVectorIndex(Protocol):
    def add(self, vector_id: str, vector: list[float]) -> None:
        ...

    def search(
        self, query: list[float], top_k: int = 10
    ) -> list[tuple[str, float]]:
        ...


class DenseIndexingService:
    """端到端：文档块 -> embedding -> 向量索引 -> Dense 检索。"""

    def __init__(
        self,
        session: AsyncSession,
        client: EmbeddingClient,
        index: DenseVectorIndex,
    ) -> None:
        self.session = session
        self.client = client
        self.index = index

    async def index_blocks(
        self,
        *,
        document_version_id: uuid.UUID | None = None,
        batch_size: int = 32,
    ) -> int:
        blocks = await NormalizedBlockStore(self.session).list_blocks(
            document_version_id=document_version_id
        )
        total = 0
        for start in range(0, len(blocks), batch_size):
            batch = blocks[start : start + batch_size]
            pairs = [(str(block.id), block.text) for block in batch]
            vectors = await self.client.embed([text for _, text in pairs])
            for (block_id, _), vector in zip(pairs, vectors, strict=True):
                self.index.add(block_id, vector)
            total += len(batch)
        return total

    async def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        vector = (await self.client.embed([query]))[0]
        return self.index.search(vector, top_k)
