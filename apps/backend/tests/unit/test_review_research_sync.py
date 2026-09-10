from __future__ import annotations

import uuid
from typing import Any, cast

from stock_research.review import research_sync


class _FakeStore:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.statuses: list[str] = []

    async def append_event(
        self,
        task_id: uuid.UUID,
        event_type: str,
        **kwargs: Any,
    ) -> None:
        self.events.append((event_type, kwargs))

    async def update_task_status(self, task_id: uuid.UUID, status: str) -> None:
        self.statuses.append(status)


class _FakeOutboxEvent:
    event_type = "research.approved"


class _FakePublisher:
    def __init__(self, session: Any) -> None:
        self.published: list[dict[str, Any]] = []

    async def publish(self, **kwargs: Any) -> _FakeOutboxEvent | None:
        self.published.append(kwargs)
        return _FakeOutboxEvent()


async def test_approved_review_completes_task_and_enqueues_outbox(
    monkeypatch: Any,
) -> None:
    store = _FakeStore()
    publisher = _FakePublisher(object())
    monkeypatch.setattr(research_sync, "WorkflowEventStore", lambda _session: store)
    monkeypatch.setattr(research_sync, "OutboxPublisher", lambda _session: publisher)
    review = cast(
        Any,
        type(
            "_Review",
            (),
            {
                "id": uuid.uuid4(),
                "target_type": "research_task",
                "target_id": str(uuid.uuid4()),
            },
        )(),
    )

    await research_sync.apply_research_review_decision(
        object(),  # type: ignore[arg-type]
        review,
        "APPROVED",
    )

    assert store.statuses == ["completed"]
    assert publisher.published[0]["event_type"] == "research.approved"
    assert [event_type for event_type, _ in store.events] == [
        "human_review.decided",
        "outbox.enqueued",
    ]


async def test_rejected_review_rejects_task(monkeypatch: Any) -> None:
    store = _FakeStore()
    monkeypatch.setattr(research_sync, "WorkflowEventStore", lambda _session: store)
    monkeypatch.setattr(
        research_sync,
        "OutboxPublisher",
        lambda _session: _FakePublisher(_session),
    )
    review = cast(
        Any,
        type(
            "_Review",
            (),
            {
                "id": uuid.uuid4(),
                "target_type": "research_task",
                "target_id": str(uuid.uuid4()),
            },
        )(),
    )

    await research_sync.apply_research_review_decision(
        object(),  # type: ignore[arg-type]
        review,
        "REJECTED",
    )

    assert store.statuses == ["rejected"]
