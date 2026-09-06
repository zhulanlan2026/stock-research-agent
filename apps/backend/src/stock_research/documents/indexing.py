from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.documents.normalization import build_text_block
from stock_research.documents.parsers import parser_for
from stock_research.documents.store import NormalizedBlockStore
from stock_research.retrieval.dense_indexing import DenseIndexer


class DocumentIndexingService:
    """文档处理编排：解析 -> 归一化块 -> 向量化。"""

    def __init__(
        self,
        session: AsyncSession,
        dense_indexing: DenseIndexer,
    ) -> None:
        self.session = session
        self.dense_indexing = dense_indexing

    async def process(
        self,
        *,
        document_version_id: uuid.UUID,
        parser_name: str,
        raw_content: bytes,
        filename: str,
    ) -> int:
        try:
            text = parser_for(parser_name).parse(raw_content, filename)
            await NormalizedBlockStore(self.session).create_block(
                build_text_block(document_version_id=document_version_id, text=text)
            )
            await self.session.commit()
        except Exception:
            return 0
        try:
            return await self.dense_indexing.index_blocks(
                document_version_id=document_version_id
            )
        except Exception:
            return 0
