from pathlib import Path

from akshare_collector.sources.financial import JsonLinesFinancialFactProvider


def test_load_filters_symbols(tmp_path: Path) -> None:
    path = tmp_path / "financial-facts.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"symbol":"600519.SH","metric":"revenue","period":"2025Q4","value":"1200.00","unit":"CNY","source_id":"akshare"}',
                '{"symbol":"000001.SZ","metric":"revenue","period":"2025Q4","value":"500.00","unit":"CNY","source_id":"akshare"}',
            ]
        ),
        encoding="utf-8",
    )

    records = JsonLinesFinancialFactProvider(path).load(["600519.SH"])

    assert len(records) == 1
    assert records[0]["symbol"] == "600519.SH"
