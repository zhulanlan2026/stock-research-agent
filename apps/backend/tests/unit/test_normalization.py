import uuid
from typing import Any

from stock_research.documents.normalization import build_text_block
from stock_research.documents.store import DocumentStore, NormalizedBlockStore


def test_build_text_block_hashes_text() -> None:
    draft = build_text_block(
        document_version_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        text="hello",
    )

    assert draft.content_hash
    assert draft.section == "body"
    assert draft.block_type == "text"


async def test_normalized_block_store_persists_block(db_context: Any) -> None:
    async with db_context.factory() as session:
        document, version = await DocumentStore(session).create_document_with_version(
            tenant_id=db_context.tenant_id,
            owner_id=db_context.user_id,
            document_type="pdf",
            content_hash="sha256:doc",
            raw_object_key="dev/doc.pdf",
        )
        await session.commit()

        draft = build_text_block(
            document_version_id=version.id,
            text="normalized content",
        )
        block = await NormalizedBlockStore(session).create_block(draft)
        await session.commit()

        assert block.document_version_id == version.id
        assert block.text == "normalized content"
        assert block.content_hash == draft.content_hash
