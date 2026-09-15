import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.core.config import get_settings
from stock_research.stores.models.supply_chain import Contract
from stock_research.stores.session import session_factory
from stock_research.supply_chain.neo4j_client import Neo4jPublisher
from stock_research.supply_chain.neo4j_rebuild import Neo4jRebuildService
from stock_research.supply_chain.store import SupplyChainStore

DEMO_CONTRACTS = [
    ("贵州茅台", "供应商A", "100.00"),
    ("供应商A", "原料商B", "50.00"),
    ("贵州茅台", "经销商C", "200.00"),
]


async def _cleanup_duplicate_demo_contracts(
    session: AsyncSession,
    demo_contracts: list[tuple[str, str, str]],
) -> int:
    deleted = 0
    for subject, obj, amount in demo_contracts:
        duplicates = (
            await session.execute(
                select(Contract)
                .where(
                    Contract.tenant_id.is_(None),
                    Contract.subject_org == subject,
                    Contract.object_org == obj,
                    Contract.amount == Decimal(amount),
                    Contract.currency == "CNY",
                    Contract.evidence_ids == ["demo-ev"],
                )
                .order_by(Contract.created_at.asc(), Contract.id.asc())
            )
        ).scalars().all()
        for duplicate in duplicates[1:]:
            await session.delete(duplicate)
            deleted += 1
    return deleted


async def main() -> None:
    async with session_factory() as session:
        store = SupplyChainStore(session)
        deleted = await _cleanup_duplicate_demo_contracts(session, DEMO_CONTRACTS)
        existing = {
            (
                contract.subject_org,
                contract.object_org,
                str(contract.amount.normalize()),
                contract.currency,
            )
            for contract in await store.list_contracts()
        }

        created = 0
        for subject, obj, amount in DEMO_CONTRACTS:
            key = (subject, obj, str(Decimal(amount).normalize()), "CNY")
            if key in existing:
                continue
            await store.create_contract(
                tenant_id=None,
                subject_org=subject,
                object_org=obj,
                amount=Decimal(amount),
                currency="CNY",
                evidence_ids=["demo-ev"],
            )
            existing.add(key)
            created += 1
        await session.commit()

        settings = get_settings()
        publisher = Neo4jPublisher(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        try:
            edge_count = await Neo4jRebuildService(session, publisher).rebuild()
            print(
                f"seeded supply chain: cleaned {deleted} duplicate contracts, "
                f"created {created} new contracts, "
                f"{edge_count} edge candidates published to neo4j"
            )
        finally:
            publisher.close()


if __name__ == "__main__":
    asyncio.run(main())
