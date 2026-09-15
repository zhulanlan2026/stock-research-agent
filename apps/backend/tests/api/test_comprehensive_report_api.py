from typing import Any

import httpx2 as httpx

from stock_research.main import app
from stock_research.stores.session import get_session, get_session_factory


async def _login(client: httpx.AsyncClient, db_context: Any) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": db_context.email, "password": db_context.password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


async def test_generate_comprehensive_report(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    app.dependency_overrides[get_session_factory] = lambda: db_context.factory
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            response = await client.post(
                "/api/v1/research/reports/comprehensive",
                json={"symbol": "600519.SH", "mode": "standard"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "600519.SH"
        assert "summary" in data
        assert data["summary"]
        titles = {section["title"] for section in data["sections"]}
        assert {
            "概览",
            "财务",
            "技术",
            "周期分析",
            "行情",
            "供应链",
            "新闻",
            "风险",
        }.issubset(titles)
    finally:
        app.dependency_overrides.clear()
