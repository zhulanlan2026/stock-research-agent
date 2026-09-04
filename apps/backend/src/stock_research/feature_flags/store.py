import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.core.feature_flags import FeatureFlagConfig
from stock_research.feature_flags.schemas import (
    TENANT_ALLOWLIST,
    USER_ALLOWLIST,
    FeatureFlagCreate,
)
from stock_research.stores.models.feature_flag import (
    FeatureFlag,
    FeatureFlagExposure,
    FeatureFlagRule,
)


class FeatureFlagStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_flag(self, create: FeatureFlagCreate) -> FeatureFlag:
        statement = (
            pg_insert(FeatureFlag)
            .values(
                id=uuid.uuid4(),
                key=create.key,
                environment=create.environment,
                enabled=create.enabled,
                percentage=create.percentage,
                kill_switch=create.kill_switch,
                start_at=create.start_at,
                end_at=create.end_at,
            )
            .on_conflict_do_update(
                index_elements=["key", "environment"],
                set_={
                    "enabled": create.enabled,
                    "percentage": create.percentage,
                    "kill_switch": create.kill_switch,
                    "start_at": create.start_at,
                    "end_at": create.end_at,
                },
            )
            .returning(FeatureFlag.id)
        )
        flag_id = (await self.session.execute(statement)).scalar_one()
        flag = await self.session.get(FeatureFlag, flag_id)
        if flag is None:  # pragma: no cover - defensive
            raise RuntimeError("feature flag upsert did not return a row")
        return flag

    async def list_rules(self, flag_id: uuid.UUID) -> list[FeatureFlagRule]:
        result = await self.session.execute(
            select(FeatureFlagRule).where(FeatureFlagRule.flag_id == flag_id)
        )
        return list(result.scalars().all())

    async def upsert_rule(
        self, flag_id: uuid.UUID, rule_type: str, rule_value: str
    ) -> FeatureFlagRule:
        statement = (
            pg_insert(FeatureFlagRule)
            .values(
                id=uuid.uuid4(),
                flag_id=flag_id,
                rule_type=rule_type,
                rule_value=rule_value,
            )
            .on_conflict_do_nothing(index_elements=["flag_id", "rule_type", "rule_value"])
            .returning(FeatureFlagRule.id)
        )
        rule_id = (await self.session.execute(statement)).scalar_one_or_none()
        if rule_id is not None:
            rule = await self.session.get(FeatureFlagRule, rule_id)
            if rule is not None:
                return rule
        result = await self.session.execute(
            select(FeatureFlagRule).where(
                FeatureFlagRule.flag_id == flag_id,
                FeatureFlagRule.rule_type == rule_type,
                FeatureFlagRule.rule_value == rule_value,
            )
        )
        rule = result.scalar_one()
        return rule

    async def record_exposure(
        self,
        *,
        flag_id: uuid.UUID,
        tenant_id: str | None,
        user_id: str | None,
        decision: bool,
        evaluated_at: datetime,
    ) -> FeatureFlagExposure:
        exposure = FeatureFlagExposure(
            flag_id=flag_id,
            tenant_id=tenant_id,
            user_id=user_id,
            decision=decision,
            evaluated_at=evaluated_at,
        )
        self.session.add(exposure)
        await self.session.flush()
        return exposure

    async def load_configs(self, environment: str) -> dict[str, FeatureFlagConfig]:
        result = await self.session.execute(
            select(FeatureFlag).where(FeatureFlag.environment == environment)
        )
        flags = list(result.scalars().all())

        configs: dict[str, FeatureFlagConfig] = {}
        for flag in flags:
            rules = await self.list_rules(flag.id)
            configs[flag.key] = FeatureFlagConfig(
                key=flag.key,
                enabled=flag.enabled,
                percentage=flag.percentage,
                tenant_allowlist=frozenset(
                    rule.rule_value
                    for rule in rules
                    if rule.rule_type == TENANT_ALLOWLIST
                ),
                user_allowlist=frozenset(
                    rule.rule_value
                    for rule in rules
                    if rule.rule_type == USER_ALLOWLIST
                ),
                kill_switch=flag.kill_switch,
                start_at=flag.start_at,
                end_at=flag.end_at,
            )
        return configs
