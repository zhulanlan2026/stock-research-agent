from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.supply_chain import OrganizationAlias


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

    async def resolve(self, alias: str) -> str | None:
        result = await self.session.execute(
            select(OrganizationAlias.canonical_name).where(
                OrganizationAlias.alias == alias
            )
        )
        return result.scalar_one_or_none()
