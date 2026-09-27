from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.supply_chain import RiskSnapshot


class RiskSnapshotStore:
    """持久化风险传播快照。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        tenant_id: uuid.UUID | None,
        symbol: str | None,
        initial_risk: dict[str, float],
        max_steps: int,
        damping: float,
        result: dict[str, float],
    ) -> RiskSnapshot:
        snapshot = RiskSnapshot(
            tenant_id=tenant_id,
            symbol=symbol,
            initial_risk=initial_risk,
            max_steps=max_steps,
            damping=damping,
            result=result,
        )
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def list(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[RiskSnapshot]:
        statement = select(RiskSnapshot)
        if tenant_id is not None:
            statement = statement.where(RiskSnapshot.tenant_id == tenant_id)
        result = await self.session.execute(
            statement.order_by(RiskSnapshot.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(
        self,
        *,
        tenant_id: uuid.UUID | None,
        snapshot_id: uuid.UUID,
    ) -> bool:
        row = await self.session.get(RiskSnapshot, snapshot_id)
        if row is None or (tenant_id is not None and row.tenant_id != tenant_id):
            return False
        await self.session.delete(row)
        return True
