from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from xtquant_collector.xtquant.history import parse_xt_time


@dataclass(frozen=True)
class NewsEvent:
    event_id: str
    event_type: str
    payload: dict[str, object]


RawNewsProvider = Callable[[Sequence[str], str], dict[str, list[object]]]


def normalize_news_item(
    symbol: str,
    kind: str,
    raw: object,
) -> NewsEvent:
    """将 XTQuant 新闻/公告原始记录规范化为 inbox 事件。

    这里只做确定性字段映射，不调用外部新闻 API，也不合成新闻内容。
    """
    normalized = _to_jsonable(raw)
    raw_dict = normalized if isinstance(normalized, dict) else {}
    time_ms = _time_ms(raw_dict.get("time"))
    if time_ms is None:
        time_ms = _time_ms(
            raw_dict.get("date")
            or raw_dict.get("datetime")
            or raw_dict.get("published_at")
            or raw_dict.get("publish_time")
            or raw_dict.get("ann_date")
            or raw_dict.get("notice_date")
            or raw_dict.get("create_time")
        )

    payload: dict[str, object] = {
        "symbol": symbol,
        "kind": kind,
        "time": time_ms if time_ms is not None else int(_utcnow_ms()),
        "headline": _optional_text(
            raw_dict.get("headline")
            or raw_dict.get("title")
            or raw_dict.get("announcement_title")
            or raw_dict.get("summary")
        ),
        "url": _optional_text(
            raw_dict.get("url") or raw_dict.get("link") or raw_dict.get("ann_url")
        ),
        "source": _optional_text(
            raw_dict.get("source") or raw_dict.get("publisher") or raw_dict.get("media")
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    event_id = kind + ":" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    event_type = "market.announcement" if kind == "announcement" else "market.news"
    return NewsEvent(event_id=event_id, event_type=event_type, payload=payload)


class XtQuantNewsFetcher:
    """XTQuant 新闻/公告采集适配器。

    XTQuant 公告字段随版本变化，默认不直接猜测 API；由调用方注入已经确认的
    `raw_provider`。未注入 provider 时，启用新闻采集会明确失败，而不是伪造数据。
    """

    def __init__(self, raw_provider: RawNewsProvider | None = None) -> None:
        self._raw_provider = raw_provider

    def fetch(
        self,
        symbols: Sequence[str],
        kind: str,
        *,
        limit: int = 100,
    ) -> list[NewsEvent]:
        if not symbols:
            return []
        if kind not in {"news", "announcement"}:
            raise ValueError(f"unsupported news kind: {kind}")
        if self._raw_provider is None:
            raise RuntimeError(
                "XTQuant news provider is not configured; "
                "confirm the announcement API fields before enabling news collection"
            )

        grouped = self._raw_provider(list(symbols), kind)
        events: list[NewsEvent] = []
        for symbol in symbols:
            for raw in grouped.get(str(symbol), [])[:limit]:
                events.append(normalize_news_item(str(symbol), kind, raw))
        return events


class XtQuantAnnouncementProvider:
    """基于 `xtdata.get_market_data(period='announcement')` 的公告 provider。

    XTQuant 公告字段未在公开文档中稳定列出，因此这里只保证函数调用正确，
    并把返回的 DataFrame/列表转换成通用 raw records，再由 normalize_news_item
    做字段别名映射。字段变化时只需在 Windows 环境中校正映射。
    """

    def __call__(
        self,
        symbols: Sequence[str],
        kind: str,
    ) -> dict[str, list[object]]:
        if kind != "announcement":
            raise RuntimeError(
                "news provider is not configured; only announcement is supported"
            )
        try:
            from xtquant import xtdata  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "xtquant is not installed; run the collector on Windows MiniQMT"
            ) from exc

        data = xtdata.get_market_data(
            stock_list=list(symbols),
            period="announcement",
            field_list=[],
            start_time="",
            end_time="",
            count=100,
        )
        return _grouped_announcement_records(data, list(symbols))


def _grouped_announcement_records(
    data: object,
    symbols: Sequence[str],
) -> dict[str, list[object]]:
    grouped: dict[str, list[object]] = {}
    if not isinstance(data, dict):
        return grouped

    frames = _find_symbol_frames(cast_dict(data), list(symbols))
    for symbol in symbols:
        frame = frames.get(symbol)
        if frame is None:
            continue
        grouped[symbol] = _frame_to_records(frame)
    return grouped


def _find_symbol_frames(
    data: dict[Any, Any],
    symbols: list[str],
) -> dict[str, object]:
    frames: dict[str, object] = {}
    for symbol in symbols:
        direct = data.get(symbol)
        if direct is not None:
            frames[symbol] = direct
    if frames:
        return frames

    for value in data.values():
        if not isinstance(value, dict):
            continue
        for symbol in symbols:
            if symbol in value:
                frames[symbol] = value[symbol]
    return frames


def _frame_to_records(frame: object) -> list[object]:
    if isinstance(frame, list):
        return frame
    if isinstance(frame, dict):
        column_records = _records_from_column_dict(frame)
        if column_records is not None:
            return column_records
        return [frame]
    to_dict = getattr(frame, "to_dict", None)
    reset_index = getattr(frame, "reset_index", None)
    if callable(to_dict) and callable(reset_index):
        reset = reset_index()
        reset_to_dict = getattr(reset, "to_dict", None)
        if not callable(reset_to_dict):
            return [frame]
        records = reset_to_dict(orient="records")
        return [dict(record) for record in records] if isinstance(records, list) else []
    return [frame]


def _records_from_column_dict(data: dict[Any, Any]) -> list[object] | None:
    if not data:
        return None
    if not all(
        isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes))
        for value in data.values()
    ):
        return None

    lengths = {len(value) for value in data.values()}
    if len(lengths) != 1:
        return None
    length = next(iter(lengths))
    keys = [str(key) for key in data]
    records: list[object] = []
    for index in range(length):
        records.append(
            {
                key: data[original_key][index]
                for key, original_key in zip(keys, data, strict=True)
            }
        )
    return records


def cast_dict(value: object) -> dict[Any, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _to_jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]

    item = getattr(value, "item", None)
    if callable(item):
        return _to_jsonable(item())

    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _time_ms(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number != number or number <= 0:
            return None
        return int(number if number > 10_000_000_000 else number * 1000)

    text = str(value).strip()
    if text.isdigit() and len(text) in {8, 14}:
        try:
            return parse_xt_time(text)
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    except ValueError:
        return None


def _utcnow_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)
