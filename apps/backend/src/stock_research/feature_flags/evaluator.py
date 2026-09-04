from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.core.feature_flags import FeatureFlagService
from stock_research.feature_flags.store import FeatureFlagStore


class FeatureFlagEvaluator:
    """业务调用点：从数据库加载灰度配置，决策并记录曝光。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.store = FeatureFlagStore(session)
        self._service_cache: dict[str, FeatureFlagService] = {}

    async def is_enabled(
        self,
        key: str,
        *,
        environment: str = "production",
        tenant_id: str | None = None,
        user_id: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        service = self._service_cache.get(environment)
        if service is None:
            configs = await self.store.load_configs(environment)
            service = FeatureFlagService(configs=configs)
            self._service_cache[environment] = service

        decision = service.is_enabled(
            key, tenant_id=tenant_id, user_id=user_id, now=now
        )

        flag = await self.store.get_flag(key, environment)
        if flag is not None:
            await self.store.record_exposure(
                flag_id=flag.id,
                tenant_id=tenant_id,
                user_id=user_id,
                decision=decision,
                evaluated_at=now or datetime.now(timezone.utc),
            )
        return decision
