from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.iam.service import PermissionService
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/users", tags=["iam"])


@router.get("/me/permissions", response_model=list[str])
async def my_permissions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    codes = await PermissionService(session).permission_codes_for_user(current_user.id)
    return sorted(codes)
