from __future__ import annotations

from typing import Protocol

from stock_research.core.config import get_settings

RAW_BUCKET = "raw-documents"


class RawObjectStore(Protocol):
    async def put_object(
        self,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        ...


class MinioRawObjectStore:
    """把上传文件写入 MinIO 原始桶，PostgreSQL 保存元数据真相。"""

    def __init__(self) -> None:
        settings = get_settings()
        from minio import Minio

        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    async def put_object(
        self,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        import io

        from minio.error import S3Error

        if not self._client.bucket_exists(RAW_BUCKET):
            self._client.make_bucket(RAW_BUCKET)
        try:
            self._client.put_object(
                RAW_BUCKET,
                object_key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error:
            raise
