from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from stock_research.supply_chain.lifecycle import OrderLifecycleService
from stock_research.supply_chain.store import SupplyChainStore


async def test_order_lifecycle_transitions_and_appends_event(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = SupplyChainStore(session)
        contract = await store.create_contract(
            tenant_id=db_context.tenant_id,
            subject_org="公司A",
            object_org="公司B",
            amount=Decimal("100"),
            currency="CNY",
        )
        order = await store.create_order(
            tenant_id=db_context.tenant_id,
            contract_id=contract.id,
            order_no="PO-1",
            amount=Decimal("100"),
            currency="CNY",
            order_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        await session.commit()

        lifecycle = OrderLifecycleService(session)
        event = await lifecycle.transition(order, "CONFIRMED", reason="已确认")
        await session.commit()

        assert order.status == "CONFIRMED"
        assert event.from_status == "CREATED"
        assert event.to_status == "CONFIRMED"


async def test_order_lifecycle_rejects_invalid_transition(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = SupplyChainStore(session)
        contract = await store.create_contract(
            tenant_id=db_context.tenant_id,
            subject_org="公司A",
            object_org="公司B",
            amount=Decimal("100"),
            currency="CNY",
        )
        order = await store.create_order(
            tenant_id=db_context.tenant_id,
            contract_id=contract.id,
            order_no="PO-1",
            amount=Decimal("100"),
            currency="CNY",
            order_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        await session.commit()

        with pytest.raises(ValueError):
            await OrderLifecycleService(session).transition(order, "DELIVERED")
