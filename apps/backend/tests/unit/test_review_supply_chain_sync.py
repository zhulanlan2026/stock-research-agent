import uuid
from typing import Any, cast

from stock_research.review import supply_chain_sync


class _FakePublisher:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeRebuildService:
    def __init__(self, session: Any, publisher: Any) -> None:
        self.session = session
        self.publisher = publisher

    async def rebuild(self) -> int:
        return 1


async def test_approved_supply_chain_review_rebuilds_graph(
    monkeypatch: Any,
) -> None:
    publisher = _FakePublisher()
    rebuild_calls: list[_FakeRebuildService] = []

    monkeypatch.setattr(
        supply_chain_sync,
        "Neo4jPublisher",
        lambda *_args, **_kwargs: publisher,
    )
    monkeypatch.setattr(
        supply_chain_sync,
        "Neo4jRebuildService",
        lambda session, pub: _capture(
            rebuild_calls,
            _FakeRebuildService(session, pub),
        ),
    )
    review = cast(
        Any,
        type(
            "_Review",
            (),
            {
                "id": uuid.uuid4(),
                "target_type": "supply_chain_graph",
                "target_id": "600519.SH",
            },
        )(),
    )

    await supply_chain_sync.apply_supply_chain_review_decision(
        object(),  # type: ignore[arg-type]
        review,
        "APPROVED",
    )

    assert len(rebuild_calls) == 1
    assert publisher.closed is True


def _capture(
    rebuild_calls: list[_FakeRebuildService],
    service: _FakeRebuildService,
) -> _FakeRebuildService:
    rebuild_calls.append(service)
    return service


async def test_non_approved_supply_chain_review_does_not_rebuild(
    monkeypatch: Any,
) -> None:
    rebuild_calls: list[Any] = []
    monkeypatch.setattr(
        supply_chain_sync,
        "Neo4jPublisher",
        lambda *_args, **_kwargs: _FakePublisher(),
    )
    monkeypatch.setattr(
        supply_chain_sync,
        "Neo4jRebuildService",
        lambda session, pub: rebuild_calls.append(object()),
    )
    review = cast(
        Any,
        type(
            "_Review",
            (),
            {
                "id": uuid.uuid4(),
                "target_type": "supply_chain_graph",
                "target_id": "600519.SH",
            },
        )(),
    )

    await supply_chain_sync.apply_supply_chain_review_decision(
        object(),  # type: ignore[arg-type]
        review,
        "REJECTED",
    )

    assert rebuild_calls == []
