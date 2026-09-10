import asyncio

import httpx2 as httpx

from stock_research.main import app


def test_metrics_endpoint_is_exposed() -> None:
    async def get_metrics() -> tuple[int, str, str]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/metrics")
        return (
            response.status_code,
            response.text,
            response.headers.get("content-type", ""),
        )

    status_code, body, content_type = asyncio.run(get_metrics())

    assert status_code == 200
    assert "text/plain" in content_type
    assert isinstance(body, str)
