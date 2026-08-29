from collections.abc import AsyncIterator

from stock_research.documents.storage import MinioRawObjectStore, RawObjectStore


async def get_raw_object_store() -> AsyncIterator[RawObjectStore]:
    yield MinioRawObjectStore()
