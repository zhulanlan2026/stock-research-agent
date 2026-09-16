from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from xtquant_collector.xtquant import (
    FinancialFactFetcher,
    JsonLinesFinancialFactProvider,
    normalize_financial_fact,
)


def test_normalize_financial_fact_is_deterministic() -> None:
    raw: dict[str, object] = {
        "symbol": "600519.SH",
        "metric": "revenue",
        "period": "2025Q4",
        "value": "1200.00",
        "unit": "CNY",
        "source_id": "real-source",
        "disclosed_at": 1767225600000,
        "available_at": 1767225600000,
    }

    first = normalize_financial_fact(raw)
    second = normalize_financial_fact(raw)

    assert first == second
    assert first.event_type == "financial.fact"
    assert first.payload["metric"] == "revenue"


def test_json_lines_financial_provider_reads_matching_symbols(
    tmp_path: Path,
) -> None:
    path = tmp_path / "financial-facts.jsonl"
    path.write_text(
        json.dumps(
            {
                "symbol": "600519.SH",
                "metric": "revenue",
                "period": "2025Q4",
                "value": "1200.00",
                "source_id": "real-source",
            },
            ensure_ascii=False,
        )
        + "\n"
        + json.dumps(
            {
                "symbol": "000001.SZ",
                "metric": "revenue",
                "period": "2025Q4",
                "value": "800.00",
                "source_id": "real-source",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    events = FinancialFactFetcher(
        JsonLinesFinancialFactProvider(path)
    ).fetch(["600519.SH"])

    assert len(events) == 1
    assert events[0].payload["symbol"] == "600519.SH"
    assert events[0].payload["value"] == "1200.00"


def test_financial_fetcher_skips_other_symbols() -> None:
    def provider(symbols: Sequence[str]) -> list[dict[str, object]]:
        return [
            {
                "symbol": "000001.SZ",
                "metric": "revenue",
                "period": "2025Q4",
                "value": "800.00",
                "source_id": "real-source",
            }
        ]

    assert FinancialFactFetcher(provider).fetch(["600519.SH"]) == []
