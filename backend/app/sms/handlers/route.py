"""Saved-route management handlers that leave traffic delivery unchanged."""

from __future__ import annotations

from pydantic import ValidationError

from app.schemas.saved_route import SavedRouteCreate
from app.services.saved_route_service import SavedRouteConflictError, SavedRouteService
from app.sms.context import SMSContext
from app.sms.handlers.traffic import _onboarding_response
from app.sms.intents import SMSIntent
from app.sms.models import SMSResponse
from app.sms.route_commands import parse_route_alias, parse_save_route


def _command_text(context: SMSContext) -> str:
    return context.resolved_text or context.normalized_text


async def handle_save_route(context: SMSContext) -> SMSResponse:
    """Create a custom route for the authenticated phone owner."""

    intent = context.intent or SMSIntent.SAVE_ROUTE
    if context.user is None:
        return _onboarding_response(intent)
    parsed = parse_save_route(_command_text(context))
    if parsed is None:
        return SMSResponse(False, intent, "Use SAVE ROUTE NAME ORIGIN TO DESTINATION.")

    name, origin, destination = parsed
    try:
        route = SavedRouteService(context.db).create(
            context.user.id,
            SavedRouteCreate(name=name, origin_text=origin, destination_text=destination),
        )
    except ValidationError as exc:
        return SMSResponse(False, intent, exc.errors()[0]["msg"])
    except SavedRouteConflictError:
        return SMSResponse(False, intent, f"A saved route named {name.upper()} already exists.")

    return SMSResponse(
        True,
        intent,
        f"Saved route {route.name.upper()}: {route.origin_text} to {route.destination_text}. Text ROUTE {route.name.upper()} anytime for traffic.",
    )


async def handle_list_routes(context: SMSContext) -> SMSResponse:
    """Return a concise private route list suitable for SMS delivery."""

    intent = context.intent or SMSIntent.LIST_ROUTES
    if context.user is None:
        return _onboarding_response(intent)
    routes = [route for route in SavedRouteService(context.db).list_for_user(context.user.id) if route.is_active and route.sms_enabled]
    if not routes:
        return SMSResponse(True, intent, "No saved routes yet. Text SAVE ROUTE NAME ORIGIN TO DESTINATION.")
    summaries = [f"{route.name.upper()} ({route.origin_text} to {route.destination_text})" for route in routes[:3]]
    suffix = "" if len(routes) <= 3 else f" +{len(routes) - 3} more"
    return SMSResponse(True, intent, f"Saved routes: {'; '.join(summaries)}{suffix}. Text ROUTE NAME for traffic.")


async def handle_delete_route(context: SMSContext) -> SMSResponse:
    """Delete only a route belonging to the inbound SMS user."""

    intent = context.intent or SMSIntent.DELETE_ROUTE
    if context.user is None:
        return _onboarding_response(intent)
    alias = parse_route_alias(_command_text(context))
    if not alias:
        return SMSResponse(False, intent, "Use DELETE ROUTE NAME.")
    service = SavedRouteService(context.db)
    route = service.get_by_alias(context.user.id, alias)
    if route is None:
        return SMSResponse(False, intent, f"No saved route named {alias.upper()} was found.")
    service.delete(context.user.id, route.id)
    return SMSResponse(True, intent, f"Deleted route {route.name.upper()}.")
