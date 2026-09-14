"""One error envelope for the whole API: ``{"detail": str, "code": str, ...}``.

Raise ``ApiError`` from services/routers; the handler renders it. FastAPI's own
``HTTPException`` (used by auth) is wrapped too so clients see one shape.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.extra = extra


class NotFound(ApiError):
    def __init__(self, what: str = "Resource") -> None:
        super().__init__(404, "not_found", f"{what} not found")


class Conflict(ApiError):
    def __init__(self, detail: str, code: str = "conflict", **extra: Any) -> None:
        super().__init__(409, code, detail, **extra)


class Invalid(ApiError):
    def __init__(self, detail: str, code: str = "invalid", **extra: Any) -> None:
        super().__init__(422, code, detail, **extra)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code, **exc.extra},
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found"}.get(
            exc.status_code, "error"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail), "code": code},
            headers=exc.headers,
        )
