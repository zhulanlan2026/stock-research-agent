import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.iam.permissions import permissions_for_roles
from stock_research.stores.models.iam import Role, UserRole


class PermissionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def permission_codes_for_user(self, user_id: uuid.UUID) -> frozenset[str]:
        roles = (
            await self.session.execute(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
            )
        ).scalars().all()
        return permissions_for_roles(roles)
