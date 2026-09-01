import uuid

from stock_research.documents.storage import MinioRawObjectStore


async def test_minio_raw_object_store_roundtrip() -> None:
    store = MinioRawObjectStore()
    key = f"drill/{uuid.uuid4().hex}.pdf"
    payload = b"%PDF-1.4 minio roundtrip"

    try:
        await store.put_object(key, payload, "application/pdf")
        assert await store.object_exists(key) is True
        assert await store.get_object(key) == payload
    finally:
        await store.delete_object(key)
        assert await store.object_exists(key) is False
