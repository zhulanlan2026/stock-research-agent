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


async def test_create_task_idempotency(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "task-1"}
            body = {"symbol": "600519.SH", "mode": "standard", "modules": ["fundamental"]}

            first = await client.post("/api/v1/research/tasks", json=body, headers=headers)
            second = await client.post("/api/v1/research/tasks", json=body, headers=headers)

            assert first.status_code == 202
            assert second.status_code == 202
            assert first.json()["id"] == second.json()["id"]
    finally:
        app.dependency_overrides.clear()
