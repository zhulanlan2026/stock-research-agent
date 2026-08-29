from typing import Any

import httpx2 as httpx

from stock_research.documents.dependencies import get_raw_object_store
from stock_research.main import app
from stock_research.stores.session import get_session


class _FakeObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_object(
        self,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        self.objects[object_key] = data


async def _login(client: httpx.AsyncClient, db_context: Any) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": db_context.email, "password": db_context.password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


async def test_upload_file_creates_document_and_stores_raw(
    db_context: Any,
) -> None:
    fake_store = _FakeObjectStore()
    app.dependency_overrides[get_session] = db_context.override
    app.dependency_overrides[get_raw_object_store] = lambda: fake_store
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            response = await client.post(
                "/api/v1/files",
                headers={"Authorization": f"Bearer {token}"},
                data={"symbol": "600519.SH", "document_type": "pdf"},
                files={"file": ("report.pdf", b"%PDF-1.4 fake", "application/pdf")},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["document_type"] == "pdf"
        assert body["status"] == "UPLOADED"
        assert body["raw_object_key"] in fake_store.objects
    finally:
        app.dependency_overrides.clear()
