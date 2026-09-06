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


async def test_generate_report(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(
                "/api/v1/research/reports",
                json={"symbol": "600519.SH", "mode": "standard"},
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "600519.SH"
        assert "summary" in data
        assert data["summary"]
        assert len(data["sections"]) >= 5
        overview = next(section for section in data["sections"] if section["title"] == "概览")
        assert "risk_level" in overview["data"]
    finally:
        app.dependency_overrides.clear()
