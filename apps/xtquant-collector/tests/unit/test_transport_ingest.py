import json
from pathlib import Path

import httpx
import pytest

from xtquant_collector.transport.ingest import IngestClient, WALPump
from xtquant_collector.wal import WalStore


def _wal_with_pending(tmp_path: Path, count: int = 2) -> WalStore:
    wal = WalStore(tmp_path / "collector-local-wal.sqlite")
    wal.initialize()
    for index in range(count):
        wal.append(
            f"evt-{index}",
            "market.snapshot",
            {"symbol": f"00000{index}.SZ"},
        )
    return wal


async def test_ingest_client_sends_expected_payload(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/ingest/events"
        assert request.headers["X-Collector-Token"] == "test-token"
        body = json.loads(request.content)
        assert body == {
            "events": [
                {
                    "event_id": "evt-1",
                    "event_type": "market.snapshot",
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
    wal = _wal_with_pending(tmp_path, count=0)
    wal.append("evt-1", "market.snapshot", {"symbol": "600519.SH"})
    entries = wal.list_pending()

    assert await client.send(entries) == (1, 0)
    await client.aclose()


async def test_ingest_client_disables_environment_proxies() -> None:
    client = IngestClient("http://localhost:8000/api/v1", "test-token")

    assert client._client.trust_env is False
    await client.aclose()


async def test_wal_pump_marks_sent_on_success(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={"accepted": 2, "duplicates": 0})

    wal = _wal_with_pending(tmp_path)
    client = IngestClient(
        "http://localhost:8000/api/v1",
        "test-token",
        transport=httpx.MockTransport(handler),
    )
    pump = WALPump(wal, client)

    assert await pump.drain_once() == 2
    assert wal.list_pending() == []
    await client.aclose()


async def test_wal_pump_keeps_pending_on_error(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    wal = _wal_with_pending(tmp_path)
    client = IngestClient(
        "http://localhost:8000/api/v1",
        "test-token",
        transport=httpx.MockTransport(handler),
    )
    pump = WALPump(wal, client)

    with pytest.raises(httpx.HTTPStatusError):
        await pump.drain_once()

    assert len(wal.list_pending()) == 2
    await client.aclose()


async def test_wal_pump_increments_attempts_on_error(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    wal = _wal_with_pending(tmp_path, count=1)
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
