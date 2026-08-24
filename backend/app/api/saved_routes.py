"""Authenticated API endpoints for private custom saved routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.billing.exceptions import SubscriptionRequiredError
from app.billing.repository import BillingRepository
from app.billing.service import BillingService
from app.core.database import get_db
from app.models.entities import User
from app.schemas.saved_route import (
    SavedRouteCreate,
    SavedRouteListResponse,
    SavedRouteResponse,
    SavedRouteUpdate,
)
from app.services.saved_route_service import (
    SavedRouteConflictError,
    SavedRouteNotFoundError,
    SavedRouteService,
)


router = APIRouter(prefix="/users/me/routes", tags=["saved routes"])


def get_saved_route_service(db: Session = Depends(get_db)) -> SavedRouteService:
    return SavedRouteService(db)


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SavedRouteNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SavedRouteConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    raise exc


@router.get("", response_model=SavedRouteListResponse)
def list_saved_routes(
    current_user: User = Depends(get_current_active_user),
    service: SavedRouteService = Depends(get_saved_route_service),
):
    return SavedRouteListResponse(routes=service.list_for_user(current_user.id))


@router.post("", response_model=SavedRouteResponse, status_code=status.HTTP_201_CREATED)
def create_saved_route(
    body: SavedRouteCreate,
    current_user: User = Depends(get_current_active_user),
    service: SavedRouteService = Depends(get_saved_route_service),
):
    try:
        return service.create(current_user.id, body)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.get("/{route_id}", response_model=SavedRouteResponse)
def get_saved_route(
    route_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SavedRouteService = Depends(get_saved_route_service),
):
    try:
        return service.get_for_user(current_user.id, route_id)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.patch("/{route_id}", response_model=SavedRouteResponse)
def update_saved_route(
    route_id: int,
    body: SavedRouteUpdate,
    current_user: User = Depends(get_current_active_user),
    service: SavedRouteService = Depends(get_saved_route_service),
):
    try:
        return service.update(current_user.id, route_id, body)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_route(
    route_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SavedRouteService = Depends(get_saved_route_service),
) -> Response:
    try:
        service.delete(current_user.id, route_id)
    except Exception as exc:
        raise _translate_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{route_id}/traffic")
async def saved_route_traffic(
    route_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SavedRouteService = Depends(get_saved_route_service),
    db: Session = Depends(get_db),
):
    """Build a route reply without duplicating the established traffic pipeline."""

    # Import the SMS-backed bridge only for route lookup, avoiding startup cycles.
    from app.models.traffic_request import TrafficRequest
    from app.services.traffic_service import TrafficService
    from app.sms.context import SMSContext

    try:
        route = service.get_for_user(current_user.id, route_id)
        if not route.is_active or not route.web_enabled:
            raise SavedRouteNotFoundError("Saved route was not found.")
        BillingService(BillingRepository(db)).ensure_active_subscription(current_user)
        service.mark_used(route)
    except SubscriptionRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        raise _translate_error(exc) from exc

    request = TrafficRequest(
        mode="route",
        origin=route.origin_text,
        destination=route.destination_text,
        subscriber_id=current_user.id,
    )
    context = SMSContext(
        db=db,
        phone_number=current_user.phone_e164 or "",
        user=current_user,
        subscription=None,
        normalized_text=f"TRAFFIC {route.origin_text} TO {route.destination_text}",
        raw_text="",
        tokens=(),
        parsed_arguments=(),
        timestamp=route.updated_at,
    )
    result = await TrafficService().build_reply(context, request)
    return {"message": result.message, "traffic_mode": result.metadata["traffic_mode"]}
