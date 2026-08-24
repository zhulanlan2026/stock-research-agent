from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast


@dataclass(frozen=True)
class QuoteEvent:
    event_id: str
    event_type: str
    payload: dict[str, object]


def _to_jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]

    item = getattr(value, "item", None)
    if callable(item):
        return _to_jsonable(item())

    return value


def normalize_quote(symbol: str, raw: object) -> QuoteEvent:
    normalized_raw = _to_jsonable(raw)
    if isinstance(normalized_raw, dict):
        raw_dict = cast(dict[str, object], normalized_raw)
        payload = {"symbol": symbol, **raw_dict}
    else:
        payload = {"symbol": symbol, "data": normalized_raw}

    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    event_id = "quote:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return QuoteEvent(event_id=event_id, event_type="market.quote", payload=payload)


class MarketDataSource(Protocol):
    def start(
        self,
        symbols: Sequence[str],
        on_event: Callable[[QuoteEvent], None],
    ) -> None:
        ...

    def stop(self) -> None:
        ...


class XtQuantMarketDataSource:
    """基于 MiniQMT/XTQuant 的真实行情采集适配器。"""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._subscriptions: list[int] = []
        self._xtdata: Any = None

    def start(
        self,
        symbols: Sequence[str],
        on_event: Callable[[QuoteEvent], None],
    ) -> None:
        if not symbols:
            return

        try:
            from xtquant import xtdata  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "xtquant is not installed; run the collector on Windows MiniQMT"
            ) from exc

        def callback(datas: object) -> None:
            if not isinstance(datas, dict):
                return
            for symbol, value in datas.items():
                if isinstance(value, list):
                    for item in value:
                        on_event(normalize_quote(str(symbol), item))
                else:
                    on_event(normalize_quote(str(symbol), value))

        self._xtdata = xtdata
        for symbol in symbols:
            subscription_id = xtdata.subscribe_quote(
                str(symbol),
                period="tick",
                count=0,
                callback=callback,
            )
            if subscription_id is None or subscription_id <= 0:
                self.stop()
                raise RuntimeError(f"failed to subscribe XTQuant quote: {symbol}")
            self._subscriptions.append(subscription_id)

        self._thread = threading.Thread(target=xtdata.run, name="xtquant-xtdata", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._xtdata is not None:
            for subscription_id in self._subscriptions:
                try:
                    self._xtdata.unsubscribe_quote(subscription_id)
                except Exception:
                    pass
        self._subscriptions = []
        self._xtdata = None
        self._thread = None
