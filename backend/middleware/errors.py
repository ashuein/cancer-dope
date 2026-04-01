"""Structured error handling middleware."""

import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "Unhandled error on %s %s: %s",
                request.method,
                request.url.path,
                exc,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "type": type(exc).__name__,
                    "path": str(request.url.path),
                },
            )
