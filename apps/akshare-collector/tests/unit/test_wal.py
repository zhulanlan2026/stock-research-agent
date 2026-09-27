from pathlib import Path

import pytest

from akshare_collector.wal import WalStore


@pytest.fixture
def wal_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "collector-local-wal.sqlite"


def test_append_and_deduplicate(wal_path: Path) -> None:
    store = WalStore(wal_path)
    store.initialize()

    assert store.append("evt-1", "market.bar", {"symbol": "600519.SH"}) is True
    assert store.append("evt-1", "market.bar", {"symbol": "600519.SH"}) is False

    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0].payload == {"symbol": "600519.SH"}


def test_mark_sent(wal_path: Path) -> None:
    store = WalStore(wal_path)
    store.initialize()

    store.append("evt-1", "market.bar", {"symbol": "600519.SH"})
    store.mark_sent("evt-1")

    assert store.list_pending() == []


def test_mark_failed_increments_attempts(wal_path: Path) -> None:
    store = WalStore(wal_path)
    store.initialize()

    store.append("evt-1", "market.bar", {"symbol": "600519.SH"})
    store.mark_failed("evt-1")
    store.mark_failed("evt-1")

    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0].attempts == 2
