import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.supply_chain import Contract, Order


class SupplyChainStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_contract(
        self,
        *,
        tenant_id: uuid.UUID | None,
        subject_org: str,
        object_org: str,
        amount: Decimal,
        currency: str,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        evidence_ids: list[str] | None = None,
    ) -> Contract:
        contract = Contract(
            tenant_id=tenant_id,
            subject_org=subject_org,
            object_org=object_org,
            amount=amount,
            currency=currency,
            valid_from=valid_from,
            valid_to=valid_to,
            evidence_ids=evidence_ids or [],
            status="DRAFT",
        )
        self.session.add(contract)
        await self.session.flush()
        await self.session.refresh(contract)
        return contract

    async def create_order(
        self,
        *,
        tenant_id: uuid.UUID | None,
        contract_id: uuid.UUID,
        order_no: str,
        amount: Decimal,
        currency: str,
        order_date: datetime,
    ) -> Order:
        order = Order(
            tenant_id=tenant_id,
            contract_id=contract_id,
            order_no=order_no,
            amount=amount,
            currency=currency,
            order_date=order_date,
            status="CREATED",
        )
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        return order
