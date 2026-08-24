from typing import Any

import httpx2 as httpx

from stock_research.main import app
from stock_research.stores.session import get_session

INGEST_URL = "/api/v1/ingest/events"
TOKEN = "dev-collector-token-change-me"


async def test_ingest_events_and_idempotency(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-Collector-Token": TOKEN}
            body = {
                "events": [
                    {
                        "event_id": "evt-1",
                        "event_type": "market.snapshot",
                        "payload": {"symbol": "600519.SH"},
                    }
                ]
            }

            first = await client.post(INGEST_URL, json=body, headers=headers)
            assert first.status_code == 202
            assert first.json() == {"accepted": 1, "duplicates": 0}

            second = await client.post(INGEST_URL, json=body, headers=headers)
            assert second.status_code == 202
            assert second.json() == {"accepted": 0, "duplicates": 1}
    finally:
        app.dependency_overrides.clear()


async def test_ingest_requires_valid_token(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            body = {
                "events": [
                    {
                        "event_id": "evt-2",
                        "event_type": "market.snapshot",
                        "payload": {"symbol": "600519.SH"},
                    }
                ]
            }
            response = await client.post(INGEST_URL, json=body)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    finally:
        app.dependency_overrides.clear()
