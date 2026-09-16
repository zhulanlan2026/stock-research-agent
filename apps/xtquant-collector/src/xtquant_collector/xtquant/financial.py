from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class FinancialFactEvent:
    event_id: str
    event_type: str
    payload: dict[str, object]


RawFinancialFactProvider = Callable[[Sequence[str]], list[dict[str, object]]]


def normalize_financial_fact(raw: dict[str, object]) -> FinancialFactEvent:
    """把真实财务事实记录规范化为 financial.fact inbox 事件。"""
    required = ("symbol", "metric", "period", "value", "source_id")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"missing financial fact fields: {', '.join(missing)}")

    payload: dict[str, object] = {
        "symbol": raw["symbol"],
        "metric": raw["metric"],
        "period": raw["period"],
        "value": raw["value"],
        "unit": raw.get("unit") or "CNY",
        "source_id": raw["source_id"],
        "disclosed_at": raw.get("disclosed_at") or _utcnow_ms(),
        "available_at": raw.get("available_at") or raw.get("disclosed_at") or _utcnow_ms(),
        "revision_no": raw.get("revision_no") or 1,
        "truth_status": raw.get("truth_status") or "VERIFIED",
        "metadata": raw.get("metadata") or {},
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    event_id = "financial:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return FinancialFactEvent(
        event_id=event_id,
        event_type="financial.fact",
        payload=payload,
    )


class FinancialFactFetcher:
    """从可注入的真实财务数据 provider 生成 financial.fact 事件。"""

    def __init__(self, provider: RawFinancialFactProvider) -> None:
        self._provider = provider

    def fetch(self, symbols: Sequence[str]) -> list[FinancialFactEvent]:
        raw_records = self._provider(list(symbols))
        events: list[FinancialFactEvent] = []
        for raw in raw_records:
            if raw.get("symbol") not in symbols:
                continue
            events.append(normalize_financial_fact(raw))
        return events


class JsonLinesFinancialFactProvider:
    """从本地 JSON Lines 文件读取真实财务事实。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def __call__(self, symbols: Sequence[str]) -> list[dict[str, object]]:
        if not self.path.exists():
            raise FileNotFoundError(self.path)

        wanted = set(symbols)
        records: list[dict[str, object]] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("symbol") in wanted:
                    records.append(record)
        return records


def _utcnow_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)
