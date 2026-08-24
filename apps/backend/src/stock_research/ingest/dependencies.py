import secrets

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from stock_research.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


async def require_collector_ingest(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_collector_token: str | None = Header(default=None, alias="X-Collector-Token"),
) -> None:
    settings = get_settings()
    token = x_collector_token
    if token is None and credentials is not None:
        token = credentials.credentials

    if token is None or not secrets.compare_digest(token, settings.collector_ingest_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "采集器令牌无效"},
        )
