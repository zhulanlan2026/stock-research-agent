from typing import Any

from stock_research.documents.normalization import build_text_block
from stock_research.documents.store import DocumentStore, NormalizedBlockStore
from stock_research.retrieval.dense_indexing import DenseIndexingService


class _FakeClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 0.0] for text in texts]


class _FakeIndex:
    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}
        self.searches: list[tuple[list[float], int]] = []

    def add(self, vector_id: str, vector: list[float]) -> None:
        self.vectors[vector_id] = vector

    def search(self, query: list[float], top_k: int = 10) -> list[tuple[str, float]]:
        self.searches.append((query, top_k))
        return [("block-1", 0.9)]


async def test_dense_indexing_indexes_blocks_and_searches(db_context: Any) -> None:
    async with db_context.factory() as session:
        document, version = await DocumentStore(
            session
        ).create_document_with_version(
            tenant_id=db_context.tenant_id,
            owner_id=db_context.user_id,
            document_type="pdf",
            content_hash="sha256:doc",
            raw_object_key="dev/doc.pdf",
        )
        await NormalizedBlockStore(session).create_block(
            build_text_block(document_version_id=version.id, text="白酒 营收 净利润")
        )
        await NormalizedBlockStore(session).create_block(
            build_text_block(document_version_id=version.id, text="芯片 半导体 光刻机")
        )
        await session.commit()

        client = _FakeClient()
        index = _FakeIndex()
        service = DenseIndexingService(session, client, index)

        count = await service.index_blocks(document_version_id=version.id)

        assert count == 2
        assert len(index.vectors) == 2

        results = await service.search("白酒")

        assert results == [("block-1", 0.9)]
        assert len(index.searches) == 1
