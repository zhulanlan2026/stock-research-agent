from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.supply_chain import OrganizationAlias

SYMBOL_TO_ORG = {
    "600519.SH": "贵州茅台",
    "000001.SZ": "平安银行",
    "000858.SZ": "五粮液",
    "301511.SZ": "德福科技",
    "601869.SH": "长飞光纤",
    "301183.SZ": "东田微",
    "603893.SH": "瑞芯微",
}


class OrganizationAliasService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_alias(
        self,
        *,
        tenant_id: uuid.UUID | None,
        canonical_name: str,
        alias: str,
    ) -> OrganizationAlias:
        row = OrganizationAlias(
            tenant_id=tenant_id,
            canonical_name=canonical_name,
            alias=alias,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def list_aliases(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> list[OrganizationAlias]:
        statement = select(OrganizationAlias)
        if tenant_id is not None:
            statement = statement.where(OrganizationAlias.tenant_id == tenant_id)
        result = await self.session.execute(
            statement.order_by(
                OrganizationAlias.canonical_name,
                OrganizationAlias.alias,
            )
        )
        return list(result.scalars().all())

    async def delete_alias(
        self,
        *,
        tenant_id: uuid.UUID | None,
        alias_id: uuid.UUID,
    ) -> bool:
        row = await self.session.get(OrganizationAlias, alias_id)
        if row is None or (tenant_id is not None and row.tenant_id != tenant_id):
            return False
        await self.session.delete(row)
        return True

    async def resolve(self, alias: str) -> str | None:
        result = await self.session.execute(
            select(OrganizationAlias.canonical_name).where(
                OrganizationAlias.alias == alias
            )
        )
        return result.scalar_one_or_none()

    async def resolve_symbol(self, symbol: str) -> str:
        alias = await self.resolve(symbol)
        if alias is not None:
            return alias
        return SYMBOL_TO_ORG.get(symbol, symbol)
