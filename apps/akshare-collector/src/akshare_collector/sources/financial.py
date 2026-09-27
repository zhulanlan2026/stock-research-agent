from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path


class JsonLinesFinancialFactProvider:
    """从本地 JSON Lines 文件读取真实财务事实。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self, symbols: Sequence[str]) -> list[dict[str, object]]:
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
