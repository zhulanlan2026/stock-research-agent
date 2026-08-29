import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.document import Document, DocumentVersion


class DocumentStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_document_with_version(
        self,
        *,
        tenant_id: uuid.UUID,
        owner_id: uuid.UUID,
        document_type: str,
        content_hash: str,
        raw_object_key: str,
        symbol: str | None = None,
        source_level: str | None = None,
        external_model_allowed: bool = False,
    ) -> tuple[Document, DocumentVersion]:
        document = Document(
            tenant_id=tenant_id,
            owner_id=owner_id,
            symbol=symbol,
            document_type=document_type,
            content_hash=content_hash,
            source_level=source_level,
            external_model_allowed=external_model_allowed,
            status="UPLOADED",
        )
        self.session.add(document)
        await self.session.flush()

        version = DocumentVersion(
            document_id=document.id,
            version_no=1,
            raw_object_key=raw_object_key,
            status="UPLOADED",
            uploaded_at=datetime.now(timezone.utc),
        )
        self.session.add(version)
        await self.session.flush()
        await self.session.refresh(document)
        await self.session.refresh(version)
        return document, version
