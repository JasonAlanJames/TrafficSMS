"""Ownership-scoped business operations for custom saved routes."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.saved_route import SavedRoute
from app.schemas.saved_route import SavedRouteCreate, SavedRouteUpdate, normalize_route_alias


class SavedRouteError(Exception):
    """Base error for safe saved-route API and SMS responses."""


class SavedRouteNotFoundError(SavedRouteError):
    pass


class SavedRouteConflictError(SavedRouteError):
    pass


class SavedRouteService:
    """Keep route persistence and ownership checks out of transport layers."""

    def __init__(self, db: Session):
        self._db = db

    def create(self, user_id: int, payload: SavedRouteCreate) -> SavedRoute:
        normalized_name = normalize_route_alias(payload.name)
        self._ensure_alias_available(user_id, normalized_name)
        route = SavedRoute(
            user_id=user_id,
            name=payload.name,
            normalized_name=normalized_name,
            origin_text=payload.origin_text,
            destination_text=payload.destination_text,
            description=payload.description,
            is_active=payload.is_active,
            sms_enabled=payload.sms_enabled,
            web_enabled=payload.web_enabled,
            sort_order=payload.sort_order,
        )
        return self._save(route)

    def list_for_user(self, user_id: int) -> list[SavedRoute]:
        return list(self._db.scalars(
            select(SavedRoute)
            .where(SavedRoute.user_id == user_id)
            .order_by(SavedRoute.sort_order, SavedRoute.name, SavedRoute.id)
        ))

    def get_for_user(self, user_id: int, route_id: int) -> SavedRoute:
        route = self._db.scalar(select(SavedRoute).where(
            SavedRoute.id == route_id,
            SavedRoute.user_id == user_id,
        ))
        if route is None:
            raise SavedRouteNotFoundError("Saved route was not found.")
        return route

    def get_by_alias(self, user_id: int, alias: str, *, sms_only: bool = False) -> SavedRoute | None:
        conditions = [
            SavedRoute.user_id == user_id,
            SavedRoute.normalized_name == normalize_route_alias(alias),
            SavedRoute.is_active.is_(True),
        ]
        if sms_only:
            conditions.append(SavedRoute.sms_enabled.is_(True))
        return self._db.scalar(select(SavedRoute).where(*conditions))

    def update(self, user_id: int, route_id: int, payload: SavedRouteUpdate) -> SavedRoute:
        route = self.get_for_user(user_id, route_id)
        values = payload.model_dump(exclude_unset=True)
        if "name" in values:
            normalized_name = normalize_route_alias(values["name"])
            self._ensure_alias_available(user_id, normalized_name, excluding_id=route.id)
            route.name = values.pop("name")
            route.normalized_name = normalized_name
        for field_name, value in values.items():
            setattr(route, field_name, value)
        return self._save(route)

    def delete(self, user_id: int, route_id: int) -> None:
        self._db.delete(self.get_for_user(user_id, route_id))
        self._db.commit()

    def mark_used(self, route: SavedRoute) -> SavedRoute:
        route.last_used_at = datetime.now(UTC)
        return self._save(route)

    def _ensure_alias_available(self, user_id: int, normalized_name: str, *, excluding_id: int | None = None) -> None:
        statement = select(SavedRoute.id).where(
            SavedRoute.user_id == user_id,
            SavedRoute.normalized_name == normalized_name,
        )
        if excluding_id is not None:
            statement = statement.where(SavedRoute.id != excluding_id)
        if self._db.scalar(statement) is not None:
            raise SavedRouteConflictError("A saved route with that name already exists.")

    def _save(self, route: SavedRoute) -> SavedRoute:
        try:
            self._db.add(route)
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise SavedRouteConflictError("A saved route with that name already exists.") from exc
        self._db.refresh(route)
        return route
