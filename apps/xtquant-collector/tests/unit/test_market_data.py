import pytest

from xtquant_collector.xtquant import XtQuantMarketDataSource, normalize_quote


class _FakeScalar:
    def item(self) -> float:
        return 9.2


def test_normalize_quote_merges_symbol_into_payload() -> None:
    event = normalize_quote("600519.SH", {"time": 1703228400000, "lastPrice": 9.2})

    assert event.event_type == "market.quote"
    assert event.payload["symbol"] == "600519.SH"
    assert event.payload["lastPrice"] == 9.2


def test_normalize_quote_is_deterministic() -> None:
    raw = {"time": 1703228400000, "lastPrice": 9.2}
    first = normalize_quote("600519.SH", raw)
    second = normalize_quote("600519.SH", raw)

    assert first.event_id == second.event_id
    assert first == second


def test_normalize_quote_coerces_numpy_style_scalar() -> None:
    event = normalize_quote("600519.SH", {"lastPrice": _FakeScalar()})

    assert event.payload["lastPrice"] == 9.2


def test_xtquant_data_source_requires_xtquant() -> None:
    source = XtQuantMarketDataSource()

    with pytest.raises(RuntimeError, match="xtquant is not installed"):
        source.start(["600519.SH"], lambda event: None)
