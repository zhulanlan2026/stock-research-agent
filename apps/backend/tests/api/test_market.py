from datetime import datetime, timezone
from typing import Any

import httpx2 as httpx

from stock_research.main import app
from stock_research.market.consumer import MarketDataConsumer
from stock_research.stores.models.workflow import InboxEvent
from stock_research.stores.session import get_session


async def test_list_market_snapshots(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        async with db_context.factory() as session:
            session.add(
                InboxEvent(
                    event_id="evt-market-1",
                    event_type="market.snapshot",
                    payload={"symbol": "600519.SH", "time": 1703228400000, "lastPrice": 9.2},
                    received_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
            await MarketDataConsumer(session).consume_pending()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": db_context.email, "password": db_context.password},
            )
            assert login.status_code == 200
            token = login.json()["access_token"]

            response = await client.get(
                "/api/v1/market/snapshots/600519.SH",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["symbol"] == "600519.SH"
            assert data[0]["payload"]["lastPrice"] == 9.2
    finally:
        app.dependency_overrides.clear()


async def test_market_snapshot_summary(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        async with db_context.factory() as session:
            session.add(
                InboxEvent(
                    event_id="evt-market-2",
                    event_type="market.snapshot",
                    payload={
                        "symbol": "600519.SH",
                        "time": 1703228400000,
                        "lastPrice": 10.5,
                        "lastClose": 10.0,
                        "bidPrice": [10.4, 10.3],
                        "askPrice": [10.6, 10.7],
                    },
                    received_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
            await MarketDataConsumer(session).consume_pending()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": db_context.email, "password": db_context.password},
            )
            token = login.json()["access_token"]

            response = await client.get(
                "/api/v1/market/snapshots/600519.SH/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["last_price"] == 10.5
            assert data["change_pct"] == 5.0
            assert data["bid_ask_spread"] == 0.2
            assert data["sample_count"] == 1
    finally:
        app.dependency_overrides.clear()


async def test_market_bars(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        async with db_context.factory() as session:
            bars = [
                (0, 10.0, 10.5, 9.9, 10.5, 120.0),
                (1, 10.2, 10.3, 10.1, 10.2, 130.0),
            ]
            for index, (minute, open_price, high, low, close, volume) in enumerate(bars):
                session.add(
                    InboxEvent(
                        event_id=f"evt-bar-{index}",
                        event_type="market.bar",
                        payload={
                            "symbol": "600519.SH",
                            "period": "1m",
                            "time": datetime(
                                2026, 8, 23, 1, minute, 0, tzinfo=timezone.utc
                            ).timestamp()
                            * 1000,
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": volume,
                            "amount": volume * 10,
                        },
                        received_at=datetime.now(timezone.utc),
                    )
                )
            await session.commit()
            await MarketDataConsumer(session).consume_pending()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": db_context.email, "password": db_context.password},
            )
            token = login.json()["access_token"]

            response = await client.get(
                "/api/v1/market/bars/600519.SH?period=1m&limit=100",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["open"] == 10.0
            assert data[0]["close"] == 10.5
            assert data[1]["close"] == 10.2
    finally:
        app.dependency_overrides.clear()
