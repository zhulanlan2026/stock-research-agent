from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
from stock_research.iam.router import router as iam_router
from stock_research.workflow.router import router as workflow_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


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
    app.include_router(iam_router, prefix=settings.api_v1_prefix)
    app.include_router(workflow_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
