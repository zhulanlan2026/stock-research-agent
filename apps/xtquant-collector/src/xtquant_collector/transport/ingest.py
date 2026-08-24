from __future__ import annotations

import httpx

from xtquant_collector.wal import WalEntry, WalStore


class IngestClient:
    """将采集器本地 WAL 事件批量推送到后端 Ingest API。"""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        # 采集器只访问本机后端，必须忽略系统/环境代理，避免 Windows 系统代理
        # 把 localhost 请求误路由到外部代理（表现为 502 Bad Gateway）。
        self._client = httpx.AsyncClient(transport=transport, timeout=10.0, trust_env=False)

    async def send(self, entries: list[WalEntry]) -> tuple[int, int]:
        if not entries:
            return 0, 0

        response = await self._client.post(
            f"{self.base_url}/ingest/events",
            json={
                "events": [
                    {
                        "event_id": entry.event_id,
                        "event_type": entry.event_type,
                        "payload": entry.payload,
                    }
                    for entry in entries
                ]
            },
            headers={"X-Collector-Token": self.token},
        )
        response.raise_for_status()
        data = response.json()
        return int(data["accepted"]), int(data["duplicates"])

    async def aclose(self) -> None:
        await self._client.aclose()


class WALPump:
    """读取 WAL 待发送事件并推送到 Ingest API，成功后标记为已发送。"""

    def __init__(self, wal: WalStore, client: IngestClient, batch_size: int = 100) -> None:
        self.wal = wal
        self.client = client
        self.batch_size = batch_size

    async def drain_once(self) -> int:
        entries = self.wal.list_pending(self.batch_size)
        if not entries:
            return 0

        try:
            accepted, duplicates = await self.client.send(entries)
        except httpx.HTTPError:
            for entry in entries:
                self.wal.mark_failed(entry.event_id)
            raise
        if accepted + duplicates == len(entries):
            for entry in entries:
                self.wal.mark_sent(entry.event_id)
        return accepted + duplicates
