from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api import billing, stripe_webhook, twilio_webhook, users
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import User
from app.services.google_maps import google_maps
from app.services.traffic import build_traffic_reply
from app.services.traffic_parser import parse_traffic_command

logger = logging.getLogger(__name__)
settings = get_settings()
is_production = settings.app_env.strip().lower() in {"production", "prod"}

HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    423: "resource_locked",
    429: "rate_limited",
    500: "internal_server_error",
    502: "upstream_error",
    503: "service_unavailable",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Database schema is managed by Alembic migrations.
    yield


def _error_payload(
    *,
    status_code: int,
    detail: str,
    error: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "detail": detail,
        "error": error or HTTP_ERROR_CODES.get(status_code, "request_failed"),
        "status_code": status_code,
    }

    if errors:
        payload["errors"] = errors

    return payload


def _json_error_response(
    *,
    status_code: int,
    detail: str,
    error: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=_error_payload(
            status_code=status_code,
            detail=detail,
            error=error,
            errors=errors,
        ),
        headers=headers,
    )


def _normalize_validation_errors(
    exc: RequestValidationError,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []

    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", []) if part != "body"]
        normalized.append(
            {
                "field": ".".join(loc) or "request",
                "message": error.get("msg", "Invalid value."),
                "type": error.get("type", "validation_error"),
            }
        )

    return normalized


app = FastAPI(
    title="TrafficSMS API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), geolocation=(), microphone=()",
    )
    response.headers.setdefault("Cache-Control", "no-store")

    if is_production:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _json_error_response(
        status_code=exc.status_code,
        detail=detail,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _json_error_response(
        status_code=422,
        detail="Validation error.",
        error="validation_error",
        errors=_normalize_validation_errors(exc),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled application error for %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _json_error_response(
        status_code=500,
        detail="Internal server error.",
        error="internal_server_error",
    )


app.include_router(auth_router)
app.include_router(users.router)
app.include_router(twilio_webhook.router)
app.include_router(stripe_webhook.router)
app.include_router(billing.router)
app.include_router(billing.admin_router)


def get_test_user(db):
    return db.scalar(
        select(User).where(
            User.email == "test@trafficsms.local"
        )
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": settings.app_env,
        "service": "TrafficSMS API",
    }


if not is_production:
    @app.get("/test/geocode")
    async def test_geocode(location: str):
        return await google_maps.geocode(location)


    @app.get("/test/route")
    async def test_google_route():
        return await google_maps.compute_route(
            "Corona, CA",
            "Riverside, CA",
        )


    @app.get("/test/traffic")
    async def test_traffic(
        text: str = "TRAFFIC CORONA"
    ):
        request = parse_traffic_command(
            text,
            subscriber_id=2,
        )

        db = SessionLocal()

        try:
            user = get_test_user(db)

            return {
                "mode": request.mode,
                "reply": await build_traffic_reply(
                    db=db,
                    request=request,
                    user=user,
                ),
            }
        finally:
            db.close()


    @app.get("/test/traffic/area")
    async def test_area():
        request = parse_traffic_command(
            "TRAFFIC CORONA",
            subscriber_id=2,
        )

        db = SessionLocal()

        try:
            user = get_test_user(db)

            return {
                "mode": request.mode,
                "reply": await build_traffic_reply(
                    db=db,
                    request=request,
                    user=user,
                ),
            }
        finally:
            db.close()


    @app.get("/test/traffic/route")
    async def test_route():
        request = parse_traffic_command(
            "TRAFFIC CORONA TO ANAHEIM",
            subscriber_id=2,
        )

        db = SessionLocal()

        try:
            user = get_test_user(db)

            return {
                "mode": request.mode,
                "reply": await build_traffic_reply(
                    db=db,
                    request=request,
                    user=user,
                ),
            }
        finally:
            db.close()


    @app.get("/test/traffic/corridor")
    async def test_corridor():
        request = parse_traffic_command(
            "TRAFFIC 91 WEST",
            subscriber_id=2,
        )

        db = SessionLocal()

        try:
            user = get_test_user(db)

            return {
                "mode": request.mode,
                "reply": await build_traffic_reply(
                    db=db,
                    request=request,
                    user=user,
                ),
            }
        finally:
            db.close()


    @app.get("/test/traffic/commute")
    async def test_commute():
        request = parse_traffic_command(
            "TRAFFIC",
            subscriber_id=2,
        )

        request.origin = "Corona, CA"
        request.destination = "Anaheim, CA"

        db = SessionLocal()

        try:
            user = get_test_user(db)

            return {
                "mode": request.mode,
                "reply": await build_traffic_reply(
                    db=db,
                    request=request,
                    user=user,
                ),
            }
        finally:
            db.close()
