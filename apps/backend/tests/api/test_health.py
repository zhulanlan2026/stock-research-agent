import asyncio

import httpx2 as httpx

from stock_research.main import app


def test_health_live() -> None:
    async def get_live() -> tuple[int, dict[str, str], str]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/live")
        return response.status_code, response.json(), response.headers.get("X-Request-ID", "")

    status_code, body, request_id = asyncio.run(get_live())
    assert status_code == 200
    assert body == {"status": "ok"}
    assert request_id
