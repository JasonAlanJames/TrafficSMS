"""Persistence and ownership tests for custom saved routes."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.models.entities import User
from app.models.saved_route import SavedRoute
from app.schemas.saved_route import SavedRouteCreate, SavedRouteUpdate
from app.services.saved_route_service import (
    SavedRouteConflictError,
    SavedRouteNotFoundError,
    SavedRouteService,
)


def _user(email: str) -> User:
    return User(email=email, phone_e164=None)


def test_saved_routes_table_and_unique_alias_constraint(db_session) -> None:
    inspector = inspect(db_session.bind)
    assert "saved_routes" in inspector.get_table_names()
    assert any(
        constraint["name"] == "uq_saved_routes_user_alias"
        for constraint in inspector.get_unique_constraints("saved_routes")
    )


def test_saved_route_service_crud_ownership_and_normalization(db_session) -> None:
    first_user = _user("first.user@trafficsms.local")
    second_user = _user("second.user@trafficsms.local")
    db_session.add_all([first_user, second_user])
    db_session.commit()
    service = SavedRouteService(db_session)

    route = service.create(first_user.id, SavedRouteCreate(
        name="  Client   Office ", origin_text=" Corona ", destination_text=" Irvine ",
    ))
    assert route.normalized_name == "CLIENT OFFICE"
    assert route.origin_text == "Corona"
    assert route.destination_text == "Irvine"
    assert service.get_by_alias(first_user.id, "client office") is route
    assert service.list_for_user(first_user.id) == [route]

    updated = service.update(first_user.id, route.id, SavedRouteUpdate(name="LAX", destination_text="LAX"))
    assert updated.normalized_name == "LAX"
    assert updated.destination_text == "LAX"
    assert service.get_by_alias(second_user.id, "LAX") is None

    service.mark_used(updated)
    assert updated.last_used_at is not None
    service.delete(first_user.id, route.id)
    assert service.list_for_user(first_user.id) == []


def test_saved_route_aliases_are_private_and_unique_per_user(db_session) -> None:
    first_user = _user("routes.one@trafficsms.local")
    second_user = _user("routes.two@trafficsms.local")
    db_session.add_all([first_user, second_user])
    db_session.commit()
    service = SavedRouteService(db_session)
    payload = SavedRouteCreate(name="Warehouse", origin_text="Home", destination_text="Warehouse")
    route = service.create(first_user.id, payload)
    assert service.create(second_user.id, payload).id != route.id

    try:
        service.create(first_user.id, payload)
    except SavedRouteConflictError:
        pass
    else:
        raise AssertionError("Expected duplicate alias rejection.")

    try:
        service.get_for_user(second_user.id, route.id)
    except SavedRouteNotFoundError:
        pass
    else:
        raise AssertionError("Expected ownership enforcement.")

    duplicate = SavedRoute(
        user_id=first_user.id,
        name="Warehouse",
        normalized_name="WAREHOUSE",
        origin_text="Elsewhere",
        destination_text="Here",
    )
    db_session.add(duplicate)
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
    else:
        raise AssertionError("Expected database-level unique alias constraint.")
