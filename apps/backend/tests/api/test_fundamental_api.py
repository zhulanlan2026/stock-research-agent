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


async def test_analyze_fundamental(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(
                "/api/v1/fundamental/analysis",
                json={"symbol": "600519.SH"},
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "600519.SH"
        assert "summary" in data
        assert "metrics" in data
        assert "净利润" in data["metrics"]
        assert "ratios" in data
    finally:
        app.dependency_overrides.clear()
