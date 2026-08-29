import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from stock_research.admin.router import router as admin_router
from stock_research.api.v1.health import router as health_router
from stock_research.auth.router import router as auth_router
from stock_research.core.config import get_settings
from stock_research.core.exception_handlers import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from stock_research.core.logging import configure_logging
from stock_research.core.middleware import RequestContextMiddleware
from stock_research.documents.router import router as documents_router
from stock_research.iam.router import router as iam_router
from stock_research.ingest.router import router as ingest_router
from stock_research.market.consumer import MarketDataConsumer
from stock_research.market.router import router as market_router
from stock_research.stores.session import session_factory
from stock_research.user_settings.router import router as user_settings_router
from stock_research.workflow.router import router as workflow_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    consume_task = asyncio.create_task(
        _consume_inbox_loop(settings.market_consume_interval_seconds)
    )
    try:
        yield
    finally:
        consume_task.cancel()
        try:
            await consume_task
        except asyncio.CancelledError:
            pass


async def _consume_inbox_loop(interval_seconds: float) -> None:
    while True:
        try:
            async with session_factory() as session:
                await MarketDataConsumer(session).consume_pending(limit=100)
        except Exception:
            logger.exception("market inbox consume failed")
        await asyncio.sleep(interval_seconds)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(admin_router, prefix=settings.api_v1_prefix)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(documents_router, prefix=settings.api_v1_prefix)
    app.include_router(iam_router, prefix=settings.api_v1_prefix)
    app.include_router(ingest_router, prefix=settings.api_v1_prefix)
    app.include_router(market_router, prefix=settings.api_v1_prefix)
    app.include_router(user_settings_router, prefix=settings.api_v1_prefix)
    app.include_router(workflow_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
