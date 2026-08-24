from pathlib import Path

import pytest

from xtquant_collector.wal import WalStore


@pytest.fixture
def wal_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "collector-local-wal.sqlite"


def test_append_and_deduplicate(wal_path: Path) -> None:
    store = WalStore(wal_path)
    store.initialize()

    assert store.append("evt-1", "market.snapshot", {"symbol": "600519.SH"}) is True
    assert store.append("evt-1", "market.snapshot", {"symbol": "600519.SH"}) is False

    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0].event_id == "evt-1"
    assert pending[0].payload == {"symbol": "600519.SH"}


def test_mark_sent(wal_path: Path) -> None:
    store = WalStore(wal_path)
    store.initialize()

    store.append("evt-1", "market.snapshot", {"symbol": "600519.SH"})
    store.mark_sent("evt-1")

    assert store.list_pending() == []


def test_pending_is_ordered_by_insertion(wal_path: Path) -> None:
    store = WalStore(wal_path)
    store.initialize()

    store.append("evt-2", "market.snapshot", {"symbol": "000001.SZ"})
    store.append("evt-1", "market.snapshot", {"symbol": "600519.SH"})

    pending = store.list_pending()
    assert [entry.event_id for entry in pending] == ["evt-2", "evt-1"]
