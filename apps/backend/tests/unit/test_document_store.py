from typing import Any

from stock_research.documents.store import DocumentStore


async def test_document_store_creates_document_and_version(db_context: Any) -> None:
    async with db_context.factory() as session:
        document, version = await DocumentStore(session).create_document_with_version(
            tenant_id=db_context.tenant_id,
            owner_id=db_context.user_id,
            document_type="pdf",
            content_hash="sha256:abc",
            raw_object_key="dev/doc.pdf",
            symbol="600519.SH",
        )
        await session.commit()

        assert document.id is not None
        assert document.status == "UPLOADED"
        assert version.document_id == document.id
        assert version.version_no == 1
        assert version.raw_object_key == "dev/doc.pdf"
