from akshare_collector.sources.records import BarRecord
from akshare_collector.sources.tushare import TushareCrossValidator


def _bar(time_ms: int, close: float) -> BarRecord:
    return BarRecord(
        symbol="600519.SH",
        period="1d",
        time_ms=time_ms,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000.0,
        amount=100000.0,
    )


def test_validator_reports_close_mismatch() -> None:
    def daily_fn(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
        return [{"trade_date": "20250102", "close": 1800.0}]

    validator = TushareCrossValidator("token", tolerance=0.005, daily_fn=daily_fn)

    mismatches = validator.validate("600519.SH", [_bar(1735776000000, 1705.0)])

    assert len(mismatches) == 1
    assert "close mismatch" in mismatches[0]


def test_validator_accepts_close_match() -> None:
    def daily_fn(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
        return [{"trade_date": "20250102", "close": 1705.0}]

    validator = TushareCrossValidator("token", tolerance=0.005, daily_fn=daily_fn)

    assert validator.validate("600519.SH", [_bar(1735776000000, 1705.0)]) == []


def test_validator_skips_without_token() -> None:
    validator = TushareCrossValidator("", tolerance=0.005)

    assert validator.validate("600519.SH", [_bar(1735776000000, 1705.0)]) == []
