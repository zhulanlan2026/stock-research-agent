from typing import Any

from stock_research.supply_chain.alias import OrganizationAliasService


async def test_organization_alias_resolves_to_canonical_name(db_context: Any) -> None:
    async with db_context.factory() as session:
        service = OrganizationAliasService(session)
        await service.add_alias(
            tenant_id=db_context.tenant_id,
            canonical_name="贵州茅台酒股份有限公司",
            alias="贵州茅台",
        )
        await session.commit()

        assert await service.resolve("贵州茅台") == "贵州茅台酒股份有限公司"
        assert await service.resolve("不存在") is None
