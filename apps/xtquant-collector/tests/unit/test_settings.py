import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from xtquant_collector.config.settings import CollectorSettings


def test_settings_defaults() -> None:
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.backend_url == "http://localhost:8000/api/v1"
    assert settings.wal_path == "./data/collector-local-wal.sqlite"
    assert settings.symbol_list == []
    assert settings.poll_interval_seconds == 1.0
    assert settings.log_level == "INFO"


def test_settings_reads_collector_prefixed_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("COLLECTOR_WAL_PATH", "/tmp/collector-local-wal.sqlite")
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.wal_path == "/tmp/collector-local-wal.sqlite"


def test_settings_parses_collect_symbols(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("COLLECTOR_COLLECT_SYMBOLS", "600519.SH, 000001.SZ")
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.symbol_list == ["600519.SH", "000001.SZ"]


def test_settings_rejects_unsupported_period() -> None:
    with pytest.raises(ValidationError):
        CollectorSettings(  # type: ignore[call-arg]
            collect_periods="1m,2m",
            _env_file=None,
        )
