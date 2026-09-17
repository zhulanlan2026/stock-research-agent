import json
from typing import Any

from stock_research.workflow.context_memory import (
    ContextMemoryCache,
    ContextMemoryService,
)
from stock_research.workflow.store import WorkflowEventStore


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


async def test_context_memory_cache_round_trip() -> None:
    cache = ContextMemoryCache(_FakeRedis())

    await cache.set_state(
        tenant_id="tenant-1",
        task_id="task-1",
        checkpoint_id="checkpoint-1",
        state={"stage": "research"},
    )
    state = await cache.get_state(
        tenant_id="tenant-1",
        task_id="task-1",
        checkpoint_id="checkpoint-1",
    )

    assert state == {"stage": "research"}
    await cache.delete(
        tenant_id="tenant-1",
        task_id="task-1",
        checkpoint_id="checkpoint-1",
    )
    assert await cache.get_state(
        tenant_id="tenant-1",
        task_id="task-1",
        checkpoint_id="checkpoint-1",
    ) is None


async def test_context_memory_service_recovers_from_postgresql(
    db_context: Any,
) -> None:
    async with db_context.factory() as session:
        task = await WorkflowEventStore(session).create_task(
            tenant_id=db_context.tenant_id,
            user_id=db_context.user_id,
            symbol="600519.SH",
            mode="standard",
            as_of=None,
            modules=["research"],
            question=None,
        )
        await session.commit()

        redis = _FakeRedis()
        cache = ContextMemoryCache(redis)
        service = ContextMemoryService(session, cache)
        await service.save_checkpoint(
            tenant_id=str(db_context.tenant_id),
            task_id=str(task.id),
            checkpoint_id=f"{task.id}:research",
            node_id="research",
            state={"stage": "research"},
        )
        await session.commit()

        cached = await service.load_checkpoint(
            tenant_id=str(db_context.tenant_id),
            task_id=str(task.id),
            checkpoint_id=f"{task.id}:research",
        )
        assert cached == {"stage": "research"}

        # 模拟 Redis 清空，必须还能从 PostgreSQL 恢复。
        redis.values.clear()
        recovered = await service.load_checkpoint(
            tenant_id=str(db_context.tenant_id),
            task_id=str(task.id),
            checkpoint_id=f"{task.id}:research",
        )
        assert recovered == {"stage": "research"}
        assert json.loads(
            redis.values[f"research:checkpoint:{db_context.tenant_id}:{task.id}:{task.id}:research"]
        ) == {"stage": "research"}
