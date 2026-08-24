import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.iam.permissions import ROLE_PERMISSIONS, permission_code_parts
from stock_research.stores.models.iam import Permission, Role, RolePermission, UserRole


class PermissionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def permission_codes_for_user(self, user_id: uuid.UUID) -> frozenset[str]:
        codes = (
            await self.session.execute(
                select(Permission.code)
                .select_from(UserRole)
                .join(Role, Role.id == UserRole.role_id)
                .join(RolePermission, RolePermission.role_id == Role.id)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(UserRole.user_id == user_id)
            )
        ).scalars().all()
        return frozenset(codes)

    async def ensure_role_permissions(self, role: Role, role_code: str) -> None:
        """Persist permissions for a role from the bootstrap catalog."""
        permission_ids: dict[str, uuid.UUID] = {}
        for code in ROLE_PERMISSIONS.get(role_code, frozenset()):
            permission = (
                await self.session.execute(select(Permission).where(Permission.code == code))
            ).scalar_one_or_none()
            if permission is None:
                resource, action = permission_code_parts(code)
                permission = Permission(code=code, resource=resource, action=action)
                self.session.add(permission)
                await self.session.flush()
            permission_ids[permission.code] = permission.id

        for permission_id in permission_ids.values():
            existing = (
                await self.session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission_id,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                self.session.add(RolePermission(role_id=role.id, permission_id=permission_id))
