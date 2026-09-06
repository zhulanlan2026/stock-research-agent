import asyncio

from sqlalchemy import select

from stock_research.review.human_review import HumanReviewService
from stock_research.stores.models.iam import Tenant
from stock_research.stores.session import session_factory


async def main() -> None:
    async with session_factory() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == "dev"))
        ).scalar_one_or_none()
        if tenant is None:
            print("tenant 'dev' not found; run seed_dev_user first")
            return

        service = HumanReviewService(session)
        for index in range(3):
            await service.create(
                tenant_id=tenant.id,
                target_type="report",
                target_id=f"report-{index + 1}",
            )
        await session.commit()
        print("seeded 3 review items for tenant dev")


if __name__ == "__main__":
    asyncio.run(main())
