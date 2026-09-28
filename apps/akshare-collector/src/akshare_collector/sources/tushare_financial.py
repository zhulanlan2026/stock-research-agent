from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from akshare_collector.sources.symbols import tushare_code
from akshare_collector.sources.timeutil import date_str, datetime_ms

FinaIndicatorRawFn = Callable[[str, str, str], list[dict[str, object]]]
DailyBasicRawFn = Callable[[str, str, str], list[dict[str, object]]]
IncomeRawFn = Callable[[str, str, str], list[dict[str, object]]]
BalancesheetRawFn = Callable[[str, str, str], list[dict[str, object]]]
CashflowRawFn = Callable[[str, str, str], list[dict[str, object]]]

_FINA_INDICATOR_METRICS: tuple[tuple[str, str], ...] = (
    ("eps", "CNY"),
    ("bps", "CNY"),
    ("roe", "percent"),
    ("roe_waa", "percent"),
    ("roa", "percent"),
    ("netprofit_margin", "percent"),
    ("grossprofit_margin", "percent"),
    ("debt_to_assets", "percent"),
    ("current_ratio", "ratio"),
    ("quick_ratio", "ratio"),
)

_DAILY_BASIC_METRICS: tuple[tuple[str, str], ...] = (
    ("pe_ttm", "multiple"),
    ("pb", "multiple"),
    ("ps_ttm", "multiple"),
    ("dv_ttm", "percent"),
    ("turnover_rate", "percent"),
    ("volume_ratio", "ratio"),
)

_INCOME_METRICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("revenue", ("total_revenue", "revenue")),
    ("net_income", ("n_income_attr_p", "n_income")),
)

_BALANCESHEET_METRICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("total_assets", ("total_assets",)),
    ("total_liabilities", ("total_liab", "total_liabilities")),
    ("total_equity", ("total_hldr_eqy_exc_min_int", "total_hldr_eqy_inc_min_int")),
    ("current_assets", ("total_cur_assets",)),
    ("current_liabilities", ("total_cur_liab",)),
)

_CASHFLOW_METRICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("operating_cash_flow", ("n_cashflow_act",)),
)


def _records(frame: Any) -> list[dict[str, object]]:
    if frame is None:
        return []
    to_dict = getattr(frame, "to_dict", None)
    if not callable(to_dict):
        return []
    records = to_dict(orient="records")
    if not isinstance(records, list):
        return []
    return [dict(record) for record in records if isinstance(record, dict)]


def _with_retry(
    fn: Callable[..., list[dict[str, object]]],
    *args: Any,
    retries: int = 3,
    delay: float = 1.0,
) -> list[dict[str, object]]:
    for attempt in range(retries):
        try:
            return fn(*args)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
    return []


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return number


def _first(row: dict[str, object], *keys: str) -> object:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _make_default_fina_indicator_fn(token: str) -> FinaIndicatorRawFn:
    import tushare as ts  # type: ignore[import-untyped]

    def fetch(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
        pro = ts.pro_api(token)
        return _records(
            pro.fina_indicator(ts_code=ts_code, start_date=start_date, end_date=end_date)
        )

    return fetch


def _make_default_daily_basic_fn(token: str) -> DailyBasicRawFn:
    import tushare as ts

    def fetch(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
        pro = ts.pro_api(token)
        return _records(
            pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
        )

    return fetch


def _make_default_income_fn(token: str) -> IncomeRawFn:
    import tushare as ts

    def fetch(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
        pro = ts.pro_api(token)
        return _records(
            pro.income(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                report_type="1",
            )
        )

    return fetch


def _make_default_balancesheet_fn(token: str) -> BalancesheetRawFn:
    import tushare as ts

    def fetch(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
        pro = ts.pro_api(token)
        return _records(
            pro.balancesheet(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                report_type="1",
            )
        )

    return fetch


def _make_default_cashflow_fn(token: str) -> CashflowRawFn:
    import tushare as ts

    def fetch(ts_code: str, start_date: str, end_date: str) -> list[dict[str, object]]:
        pro = ts.pro_api(token)
        return _records(
            pro.cashflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                report_type="1",
            )
        )

    return fetch


class TushareFinancialFactProvider:
    """从 Tushare 财务指标与每日估值指标生成 financial.fact 记录。"""

    def __init__(
        self,
        token: str,
        *,
        history_days: int = 730,
        fina_indicator_fn: FinaIndicatorRawFn | None = None,
        daily_basic_fn: DailyBasicRawFn | None = None,
        income_fn: IncomeRawFn | None = None,
        balancesheet_fn: BalancesheetRawFn | None = None,
        cashflow_fn: CashflowRawFn | None = None,
    ) -> None:
        self.token = token.strip()
        self.history_days = history_days
        self._fina_indicator_fn = fina_indicator_fn or _make_default_fina_indicator_fn(
            self.token
        )
        self._daily_basic_fn = daily_basic_fn or _make_default_daily_basic_fn(self.token)
        self._income_fn = income_fn or _make_default_income_fn(self.token)
        self._balancesheet_fn = balancesheet_fn or _make_default_balancesheet_fn(self.token)
        self._cashflow_fn = cashflow_fn or _make_default_cashflow_fn(self.token)

    def load(self, symbols: Sequence[str]) -> list[dict[str, object]]:
        if not symbols:
            return []
        if not self.token:
            raise ValueError("Tushare token is required to load financial facts")

        now = datetime.now(timezone.utc)
        start_date = date_str(now - timedelta(days=self.history_days))
        end_date = date_str(now)

        records: list[dict[str, object]] = []
        for symbol in symbols:
            ts_code = tushare_code(symbol)
            for row in _with_retry(self._fina_indicator_fn, ts_code, start_date, end_date):
                records.extend(self._fina_indicator_facts(symbol, row))
            for row in _with_retry(self._daily_basic_fn, ts_code, start_date, end_date):
                records.extend(self._daily_basic_facts(symbol, row))
            for row in _with_retry(self._income_fn, ts_code, start_date, end_date):
                records.extend(self._statement_facts(symbol, row, _INCOME_METRICS))
            for row in _with_retry(self._balancesheet_fn, ts_code, start_date, end_date):
                records.extend(self._statement_facts(symbol, row, _BALANCESHEET_METRICS))
            for row in _with_retry(self._cashflow_fn, ts_code, start_date, end_date):
                records.extend(self._statement_facts(symbol, row, _CASHFLOW_METRICS))
        return records

    def _fina_indicator_facts(
        self,
        symbol: str,
        row: dict[str, object],
    ) -> list[dict[str, object]]:
        period = _string(_first(row, "end_date", "ann_date"))
        if period is None:
            return []
        disclosed_at = datetime_ms(_first(row, "ann_date", "end_date"))
        available_at = disclosed_at or datetime_ms(_first(row, "end_date", "ann_date"))
        if available_at is None:
            return []

        facts: list[dict[str, object]] = []
        for metric, unit in _FINA_INDICATOR_METRICS:
            value = _decimal(row.get(metric))
            if value is None:
                continue
            facts.append(
                self._fact(
                    symbol=symbol,
                    metric=metric,
                    period=period,
                    value=value,
                    unit=unit,
                    disclosed_at=disclosed_at,
                    available_at=available_at,
                )
            )
        return facts

    def _daily_basic_facts(
        self,
        symbol: str,
        row: dict[str, object],
    ) -> list[dict[str, object]]:
        period = _string(_first(row, "trade_date"))
        if period is None:
            return []
        disclosed_at = datetime_ms(_first(row, "trade_date"))
        if disclosed_at is None:
            return []

        facts: list[dict[str, object]] = []
        for metric, unit in _DAILY_BASIC_METRICS:
            value = _decimal(row.get(metric))
            if value is None:
                continue
            facts.append(
                self._fact(
                    symbol=symbol,
                    metric=metric,
                    period=period,
                    value=value,
                    unit=unit,
                    disclosed_at=disclosed_at,
                    available_at=disclosed_at,
                )
            )

        # Tushare 股本与市值单位为万股/万元，这里转换为股/元，与后端契约一致。
        total_share = _decimal(row.get("total_share"))
        if total_share is not None:
            facts.append(
                self._fact(
                    symbol=symbol,
                    metric="shares_outstanding",
                    period=period,
                    value=total_share * 10_000,
                    unit="shares",
                    disclosed_at=disclosed_at,
                    available_at=disclosed_at,
                )
            )
        for metric in ("total_mv", "circ_mv"):
            value = _decimal(row.get(metric))
            if value is None:
                continue
            facts.append(
                self._fact(
                    symbol=symbol,
                    metric=metric,
                    period=period,
                    value=value * 10_000,
                    unit="CNY",
                    disclosed_at=disclosed_at,
                    available_at=disclosed_at,
                )
            )
        return facts

    def _statement_facts(
        self,
        symbol: str,
        row: dict[str, object],
        metrics: tuple[tuple[str, tuple[str, ...]], ...],
    ) -> list[dict[str, object]]:
        period = _string(_first(row, "end_date", "ann_date"))
        if period is None:
            return []
        disclosed_at = datetime_ms(_first(row, "ann_date", "f_ann_date", "end_date"))
        available_at = disclosed_at or datetime_ms(_first(row, "end_date", "ann_date"))
        if available_at is None:
            return []

        facts: list[dict[str, object]] = []
        for metric, fields in metrics:
            value = _decimal(_first(row, *fields))
            if value is None:
                continue
            facts.append(
                self._fact(
                    symbol=symbol,
                    metric=metric,
                    period=period,
                    value=value,
                    unit="CNY",
                    disclosed_at=disclosed_at,
                    available_at=available_at,
                )
            )
        return facts

    def _fact(
        self,
        *,
        symbol: str,
        metric: str,
        period: str,
        value: Decimal,
        unit: str,
        disclosed_at: int | None,
        available_at: int,
    ) -> dict[str, object]:
        return {
            "symbol": symbol,
            "metric": metric,
            "period": period,
            "value": str(value),
            "unit": unit,
            "source_id": "tushare",
            "disclosed_at": disclosed_at or available_at,
            "available_at": available_at,
        }
