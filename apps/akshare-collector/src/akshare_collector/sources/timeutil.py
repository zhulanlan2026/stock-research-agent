from __future__ import annotations

from datetime import datetime, timezone


def utcnow_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def datetime_ms(value: object) -> int | None:
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            continue
    return None


def date_str(value: datetime) -> str:
    return value.strftime("%Y%m%d")
