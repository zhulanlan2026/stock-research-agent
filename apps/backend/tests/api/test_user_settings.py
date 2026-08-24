from typing import Any

import httpx2 as httpx

from stock_research.main import app
from stock_research.stores.session import get_session


async def _login(client: httpx.AsyncClient, db_context: Any) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": db_context.email, "password": db_context.password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


async def test_put_and_get_user_setting(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            headers = {"Authorization": f"Bearer {token}"}

            put_response = await client.put(
                "/api/v1/user-settings/indicator_profiles",
                json={"value": {"profiles": [], "defaultProfileName": "", "current": {}}},
                headers=headers,
            )
            assert put_response.status_code == 200

            get_response = await client.get(
                "/api/v1/user-settings/indicator_profiles",
                headers=headers,
            )
            assert get_response.status_code == 200
            assert get_response.json()["value"]["profiles"] == []
    finally:
        app.dependency_overrides.clear()
