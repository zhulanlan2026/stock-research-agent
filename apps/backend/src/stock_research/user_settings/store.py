import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.user_setting import UserSetting


class UserSettingStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID, key: str) -> UserSetting | None:
        result = await self.session.execute(
            select(UserSetting).where(
                UserSetting.user_id == user_id,
                UserSetting.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        key: str,
        value: dict[str, object],
    ) -> UserSetting:
        statement = (
            pg_insert(UserSetting)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                key=key,
                value=value,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "key"],
                set_={"value": value},
            )
            .returning(UserSetting.id)
        )
        await self.session.execute(statement)
        return (await self.get(user_id, key))  # type: ignore[return-value]
