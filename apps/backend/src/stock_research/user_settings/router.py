from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session
from stock_research.user_settings.schemas import UserSettingResponse, UserSettingValueRequest
from stock_research.user_settings.store import UserSettingStore

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


@router.put("/{key}", response_model=UserSettingResponse)
async def put_user_setting(
    key: str = Path(min_length=1, max_length=100),
    body: UserSettingValueRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserSettingResponse:
    value = body.value if body is not None else {}
    setting = await UserSettingStore(session).upsert(
        user_id=current_user.id,
        key=key,
        value=value,
    )
    await session.commit()
    return UserSettingResponse.model_validate(setting)


@router.get("/{key}", response_model=UserSettingResponse)
async def get_user_setting(
    key: str = Path(min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserSettingResponse:
    setting = await UserSettingStore(session).get(current_user.id, key)
    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_SETTING_NOT_FOUND", "message": "用户设置不存在"},
        )
    return UserSettingResponse.model_validate(setting)
