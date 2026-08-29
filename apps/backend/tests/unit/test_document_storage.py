import io

from stock_research.documents.storage import MinioRawObjectStore


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        pass

    def release_conn(self) -> None:
        pass


class _FakeMinio:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[str, bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(
        self,
        bucket: str,
        key: str,
        data: io.BytesIO,
        length: int,
        content_type: str,
    ) -> None:
        self.objects[key] = data.read()

    def get_object(self, bucket: str, key: str) -> _FakeResponse:
        if key not in self.objects:
            raise KeyError(key)
        return _FakeResponse(self.objects[key])

    def remove_object(self, bucket: str, key: str) -> None:
        self.objects.pop(key, None)

    def stat_object(self, bucket: str, key: str) -> object:
        if key not in self.objects:
            raise KeyError(key)
        return object()


async def test_minio_raw_object_store_roundtrip() -> None:
    store = MinioRawObjectStore()
    store._client = _FakeMinio()  # type: ignore[assignment]

    await store.put_object("doc/report.pdf", b"%PDF-1.4", "application/pdf")

    assert await store.object_exists("doc/report.pdf") is True
    assert await store.get_object("doc/report.pdf") == b"%PDF-1.4"

    await store.delete_object("doc/report.pdf")

    assert await store.object_exists("doc/report.pdf") is False
    assert await store.get_object("doc/report.pdf") is None
