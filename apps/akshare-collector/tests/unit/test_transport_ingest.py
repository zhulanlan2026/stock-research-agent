import json
from pathlib import Path

import httpx
import pytest

from akshare_collector.transport.ingest import IngestClient, WALPump
from akshare_collector.wal import WalStore


def _wal(tmp_path: Path) -> WalStore:
    wal = WalStore(tmp_path / "collector-local-wal.sqlite")
    wal.initialize()
    return wal


async def test_ingest_client_sends_expected_payload(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/ingest/events"
        assert request.headers["X-Collector-Token"] == "test-token"
        assert json.loads(request.content) == {
            "events": [
                {
                    "event_id": "evt-1",
                    "event_type": "market.bar",
                    "payload": {"symbol": "600519.SH"},
                }
            ]
        }
        return httpx.Response(202, json={"accepted": 1, "duplicates": 0})

    client = IngestClient(
        "http://localhost:8000/api/v1",
        "test-token",
        transport=httpx.MockTransport(handler),
    )
    wal = _wal(tmp_path)
    wal.append("evt-1", "market.bar", {"symbol": "600519.SH"})

    assert await client.send(wal.list_pending()) == (1, 0)
    await client.aclose()


async def test_wal_pump_marks_sent_on_success(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={"accepted": 1, "duplicates": 0})

    wal = _wal(tmp_path)
    wal.append("evt-1", "market.bar", {"symbol": "600519.SH"})
    client = IngestClient(
        "http://localhost:8000/api/v1",
        "test-token",
        transport=httpx.MockTransport(handler),
    )
    pump = WALPump(wal, client)

    assert await pump.drain_once() == 1
    assert wal.list_pending() == []
    await client.aclose()


async def test_wal_pump_keeps_pending_on_error(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    wal = _wal(tmp_path)
    wal.append("evt-1", "market.bar", {"symbol": "600519.SH"})
    client = IngestClient(
        "http://localhost:8000/api/v1",
        "test-token",
        transport=httpx.MockTransport(handler),
    )
    pump = WALPump(wal, client)

    with pytest.raises(httpx.HTTPStatusError):
        await pump.drain_once()

    pending = wal.list_pending()
    assert len(pending) == 1
    assert pending[0].attempts == 1
    await client.aclose()
