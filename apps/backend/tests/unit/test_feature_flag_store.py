from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from stock_research.core.feature_flags import FeatureFlagService
from stock_research.feature_flags.evaluator import FeatureFlagEvaluator
from stock_research.feature_flags.schemas import FeatureFlagCreate
from stock_research.feature_flags.store import FeatureFlagStore
from stock_research.stores.models.feature_flag import FeatureFlagExposure


async def test_persisted_flag_drives_rollout_decision(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FeatureFlagStore(session)
        flag = await store.upsert_flag(
            FeatureFlagCreate(key="canary", environment="production", percentage=50)
        )
        await store.upsert_rule(flag.id, "user_allowlist", "vip")
        await store.upsert_rule(flag.id, "tenant_allowlist", "tenant-1")
        await session.commit()

        configs = await store.load_configs("production")

    config = configs["canary"]
    assert config.percentage == 50
    assert config.user_allowlist == frozenset({"vip"})
    assert config.tenant_allowlist == frozenset({"tenant-1"})

    service = FeatureFlagService(configs=configs)
    assert service.is_enabled("canary", user_id="vip") is True
    assert service.is_enabled("canary", tenant_id="tenant-1") is True
    assert service.is_enabled("canary", user_id="user-1") == service.is_enabled(
        "canary", user_id="user-1"
    )


async def test_upsert_flag_is_idempotent(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FeatureFlagStore(session)
        await store.upsert_flag(FeatureFlagCreate(key="canary", percentage=10))
        await session.commit()
        await store.upsert_flag(FeatureFlagCreate(key="canary", percentage=90))
        await session.commit()

        configs = await store.load_configs("production")

    assert configs["canary"].percentage == 90


async def test_record_exposure(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FeatureFlagStore(session)
        flag = await store.upsert_flag(FeatureFlagCreate(key="canary"))
        await session.commit()

        exposure = await store.record_exposure(
            flag_id=flag.id,
            tenant_id="tenant-1",
            user_id="user-1",
            decision=True,
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        await session.commit()

        assert exposure.decision is True
        assert exposure.user_id == "user-1"


async def test_evaluator_decides_and_records_exposure(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = FeatureFlagStore(session)
        flag = await store.upsert_flag(
            FeatureFlagCreate(key="canary", percentage=100)
        )
        await session.commit()

        evaluator = FeatureFlagEvaluator(session)
        assert await evaluator.is_enabled("canary", user_id="user-1") is True
        await session.commit()

        result = await session.execute(
            select(FeatureFlagExposure).where(
                FeatureFlagExposure.flag_id == flag.id
            )
        )
        exposures = list(result.scalars().all())

        assert len(exposures) == 1
        assert exposures[0].decision is True
        assert exposures[0].user_id == "user-1"
