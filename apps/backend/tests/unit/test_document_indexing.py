import uuid
from typing import Any

from stock_research.documents.indexing import DocumentIndexingService
from stock_research.documents.store import DocumentStore, NormalizedBlockStore


class _FakeDenseIndexing:
    def __init__(self) -> None:
        self.indexed_versions: list[uuid.UUID | None] = []

    async def index_blocks(
        self, *, document_version_id: uuid.UUID | None = None, batch_size: int = 32
    ) -> int:
        self.indexed_versions.append(document_version_id)
        return 1


async def test_document_indexing_parses_and_indexes(db_context: Any) -> None:
    async with db_context.factory() as session:
        _, version = await DocumentStore(
            session
        ).create_document_with_version(
            tenant_id=db_context.tenant_id,
            owner_id=db_context.user_id,
            document_type="txt",
            content_hash="sha256:doc",
            raw_object_key="dev/doc.txt",
        )
        await session.commit()

        dense = _FakeDenseIndexing()
        service = DocumentIndexingService(session, dense)

        count = await service.process(
            document_version_id=version.id,
            parser_name="text",
            raw_content="白酒 营收 净利润 增长".encode(),
            filename="report.txt",
        )

        assert count == 1
        assert dense.indexed_versions == [version.id]

        blocks = await NormalizedBlockStore(session).list_blocks(
            document_version_id=version.id
        )
        assert len(blocks) == 1
        assert blocks[0].text == "白酒 营收 净利润 增长"
