from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.supply_chain.store import SupplyChainStore


async def test_supply_chain_store_creates_contract_and_order(db_context: Any) -> None:
    async with db_context.factory() as session:
        store = SupplyChainStore(session)
        contract = await store.create_contract(
            tenant_id=db_context.tenant_id,
            subject_org="公司A",
            object_org="公司B",
            amount=Decimal("1000000.00"),
            currency="CNY",
            evidence_ids=["evidence-1"],
        )
        order = await store.create_order(
            tenant_id=db_context.tenant_id,
            contract_id=contract.id,
            order_no="PO-2026-001",
            amount=Decimal("500000.00"),
            currency="CNY",
            order_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        await session.commit()

        assert contract.status == "DRAFT"
        assert contract.evidence_ids == ["evidence-1"]
        assert order.contract_id == contract.id
        assert order.status == "CREATED"
