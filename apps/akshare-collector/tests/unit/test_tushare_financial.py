from decimal import Decimal

import pytest

from akshare_collector.sources.tushare_financial import TushareFinancialFactProvider


def _empty(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
    return []


def test_load_maps_fina_indicator_metrics() -> None:
    def fina_indicator_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        assert ts_code == "600519.SH"
        return [
            {
                "end_date": "20240930",
                "ann_date": "2024-10-28",
                "eps": 18.2,
                "roe": 12.5,
                "grossprofit_margin": 91.2,
                "current_ratio": 3.1,
                "not_a_metric": 1.0,
            }
        ]

    def daily_basic_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return []

    provider = TushareFinancialFactProvider(
        "token",
        fina_indicator_fn=fina_indicator_fn,
        daily_basic_fn=daily_basic_fn,
        income_fn=_empty,
        balancesheet_fn=_empty,
        cashflow_fn=_empty,
    )

    records = provider.load(["600519.SH"])

    by_metric = {record["metric"]: record for record in records}
    assert by_metric["eps"]["value"] == "18.2"
    assert by_metric["eps"]["unit"] == "CNY"
    assert by_metric["eps"]["period"] == "20240930"
    assert by_metric["roe"]["value"] == "12.5"
    assert by_metric["roe"]["unit"] == "percent"
    assert by_metric["current_ratio"]["unit"] == "ratio"
    assert "not_a_metric" not in by_metric


def test_load_maps_daily_basic_and_converts_units() -> None:
    def fina_indicator_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return []

    def daily_basic_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "trade_date": "20250102",
                "pe_ttm": 20.5,
                "pb": 8.0,
                "dv_ttm": 1.8,
                "total_share": 125619.78,
                "total_mv": 21000000.0,
                "circ_mv": 21000000.0,
            }
        ]

    provider = TushareFinancialFactProvider(
        "token",
        fina_indicator_fn=fina_indicator_fn,
        daily_basic_fn=daily_basic_fn,
        income_fn=_empty,
        balancesheet_fn=_empty,
        cashflow_fn=_empty,
    )

    records = provider.load(["600519.SH"])

    by_metric = {record["metric"]: record for record in records}
    assert by_metric["pe_ttm"]["value"] == "20.5"
    assert by_metric["pe_ttm"]["unit"] == "multiple"
    assert by_metric["dv_ttm"]["unit"] == "percent"
    assert Decimal(by_metric["shares_outstanding"]["value"]) == Decimal("1256197800")
    assert by_metric["shares_outstanding"]["unit"] == "shares"
    assert Decimal(by_metric["total_mv"]["value"]) == Decimal("210000000000")
    assert by_metric["total_mv"]["unit"] == "CNY"


def test_load_skips_none_and_nan_values() -> None:
    def fina_indicator_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "end_date": "20240930",
                "ann_date": "2024-10-28",
                "eps": None,
                "roe": float("nan"),
            }
        ]

    def daily_basic_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return []

    provider = TushareFinancialFactProvider(
        "token",
        fina_indicator_fn=fina_indicator_fn,
        daily_basic_fn=daily_basic_fn,
        income_fn=_empty,
        balancesheet_fn=_empty,
        cashflow_fn=_empty,
    )

    assert provider.load(["600519.SH"]) == []


def test_load_maps_statement_metrics() -> None:
    def income_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "end_date": "20240930",
                "ann_date": "2024-10-28",
                "total_revenue": 1234.5,
                "n_income_attr_p": 456.7,
            }
        ]

    def balancesheet_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "end_date": "20240930",
                "ann_date": "2024-10-28",
                "total_hldr_eqy_exc_min_int": 789.0,
            }
        ]

    def cashflow_fn(
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        return [
            {
                "end_date": "20240930",
                "ann_date": "2024-10-28",
                "n_cashflow_act": 321.0,
            }
        ]

    provider = TushareFinancialFactProvider(
        "token",
        fina_indicator_fn=_empty,
        daily_basic_fn=_empty,
        income_fn=income_fn,
        balancesheet_fn=balancesheet_fn,
        cashflow_fn=cashflow_fn,
    )

    records = provider.load(["600519.SH"])

    by_metric = {record["metric"]: record for record in records}
    assert by_metric["revenue"]["value"] == "1234.5"
    assert by_metric["revenue"]["unit"] == "CNY"
    assert by_metric["net_income"]["value"] == "456.7"
    assert by_metric["total_equity"]["value"] == "789.0"
    assert by_metric["operating_cash_flow"]["value"] == "321.0"
    assert by_metric["revenue"]["period"] == "20240930"


def test_load_requires_token() -> None:
    provider = TushareFinancialFactProvider("")

    with pytest.raises(ValueError, match="token"):
        provider.load(["600519.SH"])


def test_load_returns_empty_for_no_symbols() -> None:
    provider = TushareFinancialFactProvider("token")

    assert provider.load([]) == []
