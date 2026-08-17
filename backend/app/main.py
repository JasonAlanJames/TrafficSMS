from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import billing, stripe_webhook, twilio_webhook
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import User
from app.services.google_maps import google_maps
from app.services.traffic import build_traffic_reply
from app.services.traffic_parser import parse_traffic_command

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Database schema is managed by Alembic migrations.
    yield


app = FastAPI(
    title="TrafficSMS API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(twilio_webhook.router)
app.include_router(stripe_webhook.router)
app.include_router(billing.router)


def get_test_user(db):
    """
    Returns the local development test user.
    """

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
