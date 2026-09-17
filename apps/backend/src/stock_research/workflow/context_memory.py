from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.workflow.checkpoint_store import CheckpointStore


class ContextMemoryCache:
    """Redis 热缓存；PostgreSQL checkpoint_ref 仍是真相源。"""

    def __init__(self, client: Any, *, default_ttl_seconds: int = 3600) -> None:
        self._client = client
        self.default_ttl_seconds = default_ttl_seconds

    def _key(
        self,
        tenant_id: str,
        task_id: str,
        checkpoint_id: str,
    ) -> str:
        return f"research:checkpoint:{tenant_id}:{task_id}:{checkpoint_id}"

    async def get_state(
        self,
        *,
        tenant_id: str,
        task_id: str,
        checkpoint_id: str,
    ) -> dict[str, Any] | None:
        raw = await self._client.get(
            self._key(tenant_id, task_id, checkpoint_id)
        )
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw) if isinstance(raw, str) else None

    async def set_state(
        self,
        *,
        tenant_id: str,
        task_id: str,
        checkpoint_id: str,
        state: Mapping[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        await self._client.set(
            self._key(tenant_id, task_id, checkpoint_id),
            json.dumps(dict(state), default=str, separators=(",", ":")),
            ex=ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds,
        )

    async def delete(
        self,
        *,
        tenant_id: str,
        task_id: str,
        checkpoint_id: str,
    ) -> None:
        await self._client.delete(
            self._key(tenant_id, task_id, checkpoint_id)
        )


class ContextMemoryService:
    """统一 Checkpoint 读写：先 PostgreSQL，后 Redis。"""

    def __init__(
        self,
        session: AsyncSession,
        cache: ContextMemoryCache | None,
    ) -> None:
        self.session = session
        self.cache = cache

    async def save_checkpoint(
        self,
        *,
        tenant_id: str,
        task_id: str,
        checkpoint_id: str,
        node_id: str,
        state: dict[str, Any],
    ) -> None:
        task_uuid = uuid.UUID(task_id)
        await CheckpointStore(self.session).save(
            task_id=task_uuid,
            checkpoint_id=checkpoint_id,
            node_id=node_id,
            state=state,
        )
        await self.session.flush()
        if self.cache is not None:
            await self.cache.set_state(
                tenant_id=tenant_id,
                task_id=task_id,
                checkpoint_id=checkpoint_id,
                state=state,
            )

    async def load_checkpoint(
        self,
        *,
        tenant_id: str,
        task_id: str,
        checkpoint_id: str,
    ) -> dict[str, Any] | None:
        if self.cache is not None:
            cached = await self.cache.get_state(
                tenant_id=tenant_id,
                task_id=task_id,
                checkpoint_id=checkpoint_id,
            )
            if cached is not None:
                return cached

        row = await CheckpointStore(self.session).get(checkpoint_id)
        if row is None:
            return None
        state = dict(row.state)
        if self.cache is not None:
            await self.cache.set_state(
                tenant_id=tenant_id,
                task_id=task_id,
                checkpoint_id=checkpoint_id,
                state=state,
            )
        return state

    async def list_checkpoints(self, task_id: str) -> list[dict[str, Any]]:
        rows = await CheckpointStore(self.session).list_for_task(
            uuid.UUID(task_id)
        )
        return [
            {
                "checkpoint_id": row.checkpoint_id,
                "node_id": row.node_id,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
