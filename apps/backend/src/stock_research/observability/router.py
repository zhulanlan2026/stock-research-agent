from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from stock_research.observability.metrics import get_prometheus_registry

router = APIRouter(tags=["observability"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    return get_prometheus_registry().render()
