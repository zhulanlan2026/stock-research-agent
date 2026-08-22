from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.auth.errors import AuthError
from stock_research.auth.schemas import LoginRequest, LoginResponse, UserMe
from stock_research.auth.service import AuthService
from stock_research.core.config import get_settings
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(tags=["auth"])


def _auth_error(exc: AuthError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    service = AuthService(session)
    try:
        access_token, refresh_token, user = await service.login(
            body.email, body.password, body.tenant_slug
        )
    except AuthError as exc:
        raise _auth_error(exc) from exc

    settings = get_settings()
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(
        access_token=access_token,
        expires_in=settings.access_token_ttl_minutes * 60,
        user=UserMe.model_validate(user),
    )


@router.post("/auth/refresh", response_model=LoginResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_SESSION_REVOKED", "message": "刷新令牌不存在"},
        )

    service = AuthService(session)
    try:
        access_token, new_refresh_token, user = await service.refresh(refresh_token)
    except AuthError as exc:
        raise _auth_error(exc) from exc

    _set_refresh_cookie(response, new_refresh_token)
    return LoginResponse(
        access_token=access_token,
        expires_in=settings.access_token_ttl_minutes * 60,
        user=UserMe.model_validate(user),
    )


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> Response:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token is not None:
        service = AuthService(session)
        await service.logout(refresh_token)
    response.delete_cookie(settings.refresh_cookie_name, path="/api/v1/auth")
    return response


@router.get("/users/me", response_model=UserMe)
async def me(current_user: User = Depends(get_current_user)) -> UserMe:
    return UserMe.model_validate(current_user)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
    )
