"""Fast, dependency-free deployment health endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


def _payload(endpoint: str) -> dict[str, str]:
    return {"status": "ok", "service": "trafficsms-api", "endpoint": endpoint}


@router.get("/health")
def health() -> dict[str, str]:
    return _payload("health")


@router.get("/live")
def live() -> dict[str, str]:
    return _payload("live")


@router.get("/ready")
def ready() -> dict[str, str]:
    return _payload("ready")
