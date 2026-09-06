from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.core.config import get_settings
from stock_research.documents.indexing import DocumentIndexingService
from stock_research.documents.storage import MinioRawObjectStore, RawObjectStore
from stock_research.retrieval.dense_indexing import DenseIndexingService
from stock_research.retrieval.embedding import build_embedding_client
from stock_research.retrieval.milvus_dense import MilvusDenseIndex
from stock_research.stores.session import get_session


async def get_raw_object_store() -> AsyncIterator[RawObjectStore]:
    yield MinioRawObjectStore()


async def get_document_indexing_service(
    session: AsyncSession = Depends(get_session),
) -> DocumentIndexingService | None:
    settings = get_settings()
    client = build_embedding_client(settings)
    try:
        index = MilvusDenseIndex(
            uri=settings.milvus_uri,
            collection_name=settings.embedding_model,
            dim=settings.embedding_dim,
        )
    except Exception:
        return None
    return DocumentIndexingService(
        session,
        DenseIndexingService(session, client, index),
    )
