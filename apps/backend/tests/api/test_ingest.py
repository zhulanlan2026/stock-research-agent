from datetime import datetime, timezone
from typing import Any

import httpx2 as httpx

from stock_research.fundamental.consumer import FinancialFactConsumer
from stock_research.fundamental.store import FinancialFactStore
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


async def test_ingest_financial_fact_and_consume(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-Collector-Token": TOKEN}
            body = {
                "events": [
                    {
                        "event_id": "financial-evt-1",
                        "event_type": "financial.fact",
                        "payload": {
                            "symbol": "600519.SH",
                            "metric": "revenue",
                            "period": "2025Q4",
                            "value": "1200.00",
                            "unit": "CNY",
                            "source_id": "real-financial-source",
                            "disclosed_at": 1767225600000,
                            "available_at": 1767225600000,
                        },
                    }
                ]
            }
            response = await client.post(INGEST_URL, json=body, headers=headers)
            assert response.status_code == 202
            assert response.json() == {"accepted": 1, "duplicates": 0}

        async with db_context.factory() as session:
            assert await FinancialFactConsumer(session).consume_pending() == 1
            facts = await FinancialFactStore(session).list_for_symbol(
                symbol="600519.SH",
                as_of=datetime(2026, 1, 2, tzinfo=timezone.utc),
                metrics=["revenue"],
            )
            assert len(facts) == 1
            assert facts[0].source_id == "real-financial-source"
    finally:
        app.dependency_overrides.clear()
