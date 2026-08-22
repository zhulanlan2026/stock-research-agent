from typing import Any

import httpx2 as httpx

from stock_research.main import app
from stock_research.stores.session import get_session


async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


async def test_permission_negative(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            free_token = await _login(client, db_context.free_email, db_context.free_password)
            denied = await client.get(
                "/api/v1/admin/audit-read",
                headers={"Authorization": f"Bearer {free_token}"},
            )
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "PERMISSION_DENIED"

            admin_token = await _login(client, db_context.email, db_context.password)
            allowed = await client.get(
                "/api/v1/admin/audit-read",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert allowed.status_code == 200
    finally:
        app.dependency_overrides.clear()
