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
            "专业财务",
            "技术",
            "周期分析",
            "行情",
            "供应链",
            "新闻",
            "风险",
            "RAG 证据",
            "证据强度",
        }.issubset(titles)
        professional = next(
            section for section in data["sections"] if section["title"] == "专业财务"
        )
        assert "risk_points" in professional["data"]
        assert "dupont" in professional["data"]
        rag = next(
            section for section in data["sections"] if section["title"] == "RAG 证据"
        )
        assert "graph_evidence" in rag["data"]
        assert "agentic_rag" in rag["data"]
    finally:
        app.dependency_overrides.clear()
