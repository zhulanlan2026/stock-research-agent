import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from akshare_collector.config.settings import CollectorSettings


def test_settings_defaults(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("COLLECTOR_COLLECT_SYMBOLS", raising=False)
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.backend_url == "http://localhost:8000/api/v1"
    assert settings.wal_path == "./data/collector-local-wal.sqlite"
    assert settings.symbol_list == []
    assert settings.period_list == ["1m", "1d"]
    assert settings.collect_news_enabled is False
    assert settings.cross_validation_active is False


def test_settings_parses_symbols(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("COLLECTOR_COLLECT_SYMBOLS", "600519.SH, 000001.SZ")
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.symbol_list == ["600519.SH", "000001.SZ"]


def test_settings_cross_validation_requires_token(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("COLLECTOR_TUSHARE_TOKEN", "abc")
    settings = CollectorSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.cross_validation_active is True


def test_settings_rejects_unsupported_period() -> None:
    with pytest.raises(ValidationError):
        CollectorSettings(  # type: ignore[call-arg]
            collect_periods="1m,2m",
            _env_file=None,
        )


def test_settings_rejects_negative_tolerance() -> None:
    with pytest.raises(ValidationError):
        CollectorSettings(  # type: ignore[call-arg]
            cross_validation_tolerance=-0.1,
            _env_file=None,
        )


def test_settings_rejects_negative_bars_refresh_seconds() -> None:
    with pytest.raises(ValidationError):
        CollectorSettings(  # type: ignore[call-arg]
            bars_refresh_seconds=-1,
            _env_file=None,
        )


def test_settings_tushare_source_requires_token() -> None:
    with pytest.raises(ValidationError):
        CollectorSettings(  # type: ignore[call-arg]
            market_source="tushare",
            _env_file=None,
        )


def test_settings_rejects_unknown_market_source() -> None:
    with pytest.raises(ValidationError):
        CollectorSettings(  # type: ignore[call-arg]
            market_source="other",
            _env_file=None,
        )


def test_settings_tushare_financial_source_requires_token() -> None:
    with pytest.raises(ValidationError):
        CollectorSettings(  # type: ignore[call-arg]
            financial_source="tushare",
            _env_file=None,
        )
