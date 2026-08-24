from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


class MarketSnapshotCache:
    """Redis 热读缓存，PostgreSQL 仍是真相源，缓存只加速读取。"""

    def __init__(self, client: Any, *, default_ttl_seconds: int = 30) -> None:
        self._client = client
        self.default_ttl_seconds = default_ttl_seconds

    def _key(self, symbol: str) -> str:
        return f"market:snapshot:{symbol}:summary"

    async def get_summary(self, symbol: str) -> dict[str, Any] | None:
        raw = await self._client.get(self._key(symbol))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw) if isinstance(raw, str) else None

    async def set_summary(
        self,
        symbol: str,
        payload: Mapping[str, Any],
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        await self._client.set(
            self._key(symbol),
            json.dumps(payload, default=str, separators=(",", ":")),
            ex=ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds,
        )
