import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = structlog.get_logger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = _request_id(request)
    code = "HTTP_ERROR"
    message = str(exc.detail)
    details: object = {}

    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code", code))
        message = str(exc.detail.get("message", message))
        details = exc.detail.get("details", {})

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "request_id": request_id,
            "error": {"code": code, "message": message, "details": details},
        },
        headers={"X-Request-ID": request_id or ""},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=422,
        content={
            "request_id": request_id,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数无效",
                "details": {"errors": exc.errors()},
            },
        },
        headers={"X-Request-ID": request_id or ""},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _request_id(request)
    logger.error("unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "request_id": request_id,
            "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误", "details": {}},
        },
        headers={"X-Request-ID": request_id or ""},
    )
