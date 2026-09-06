import asyncio
from decimal import Decimal

from stock_research.core.config import get_settings
from stock_research.stores.session import session_factory
from stock_research.supply_chain.neo4j_client import Neo4jPublisher
from stock_research.supply_chain.neo4j_rebuild import Neo4jRebuildService
from stock_research.supply_chain.store import SupplyChainStore


async def main() -> None:
    async with session_factory() as session:
        store = SupplyChainStore(session)
        for subject, obj, amount in [
            ("贵州茅台", "供应商A", "100.00"),
            ("供应商A", "原料商B", "50.00"),
            ("贵州茅台", "经销商C", "200.00"),
        ]:
            await store.create_contract(
                tenant_id=None,
                subject_org=subject,
                object_org=obj,
                amount=Decimal(amount),
                currency="CNY",
                evidence_ids=["demo-ev"],
            )
        await session.commit()

        settings = get_settings()
        publisher = Neo4jPublisher(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        try:
            edge_count = await Neo4jRebuildService(session, publisher).rebuild()
            print(f"seeded supply chain: {edge_count} edges published to neo4j")
        finally:
            publisher.close()


if __name__ == "__main__":
    asyncio.run(main())
