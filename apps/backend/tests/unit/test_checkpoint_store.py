from typing import Any

from stock_research.workflow.checkpoint_store import CheckpointStore
from stock_research.workflow.store import WorkflowEventStore


async def test_checkpoint_store_saves_and_lists(db_context: Any) -> None:
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

        store = CheckpointStore(session)
        checkpoint = await store.save(
            task_id=task.id,
            checkpoint_id="checkpoint-1",
            node_id="research",
            state={"stage": "research"},
        )
        await session.commit()

        assert await store.get("checkpoint-1") is not None
        assert len(await store.list_for_task(task.id)) == 1
        assert checkpoint.state["stage"] == "research"
