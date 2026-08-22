from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.iam.service import PermissionService
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session


def require_permission(permission: str) -> Callable[..., Any]:
    async def dependency(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        codes = await PermissionService(session).permission_codes_for_user(current_user.id)
        if permission not in codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERMISSION_DENIED", "message": "权限不足"},
            )
        return current_user

    return dependency
