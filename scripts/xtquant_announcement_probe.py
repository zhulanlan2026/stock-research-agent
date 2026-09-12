from __future__ import annotations

import argparse
import json
from typing import Any


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        value = value.to_dict(orient="records")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        value = value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe XTQuant announcement data structure on Windows MiniQMT"
    )
    parser.add_argument("--symbols", default="600519.SH,000001.SZ")
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    try:
        from xtquant import xtdata  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "xtquant is not installed; run this script on the Windows MiniQMT host"
        ) from exc

    symbols = [item.strip() for item in args.symbols.split(",") if item.strip()]
    data = xtdata.get_market_data(
        stock_list=symbols,
        period="announcement",
        field_list=[],
        start_time="",
        end_time="",
        count=args.count,
    )

    print("top-level type:", type(data).__name__)
    if isinstance(data, dict):
        print("top-level keys:", list(data.keys()))
        for symbol in symbols:
            value = data.get(symbol)
            if value is None:
                print(f"\n{symbol}: <missing>")
                continue
            print(f"\n{symbol} value type: {type(value).__name__}")
            if hasattr(value, "index"):
                print("index name:", getattr(value.index, "name", None))
                print("columns:", list(value.columns))
                print("index sample:", list(value.index[:3]))
            records = _jsonable(value)
            if isinstance(records, list):
                print("records sample:")
                print(json.dumps(records[:2], ensure_ascii=False, indent=2))
            else:
                print("value sample:")
                print(json.dumps(records, ensure_ascii=False, indent=2)[:3000])
    else:
        print("data sample:")
        print(json.dumps(_jsonable(data), ensure_ascii=False, indent=2)[:3000])


if __name__ == "__main__":
    main()
