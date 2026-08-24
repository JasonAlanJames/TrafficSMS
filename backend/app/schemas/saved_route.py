"""Validation and response schemas for saved route management."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


RESERVED_ROUTE_NAMES = {
    "HELP", "STOP", "START", "TRAFFIC", "POLICE", "REPORT", "SUBSCRIBE",
    "UNSUBSCRIBE", "SETTINGS", "ROUTE", "ROUTES", "SAVE", "DELETE", "REMOVE",
    "LIST",
}


def normalize_route_alias(value: str) -> str:
    """Return the stable alias used for uniqueness and SMS matching."""

    return " ".join(value.strip().upper().split())


class SavedRouteInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    origin_text: str = Field(min_length=1, max_length=255)
    destination_text: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    sms_enabled: bool = True
    web_enabled: bool = True
    sort_order: int = Field(default=0, ge=0, le=10_000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = normalize_route_alias(value)
        if not normalized:
            raise ValueError("Route name is required.")
        if normalized in RESERVED_ROUTE_NAMES:
            raise ValueError("Route name conflicts with a reserved SMS command.")
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9 -]*", normalized):
            raise ValueError("Route name may contain only letters, numbers, spaces, and hyphens.")
        return " ".join(value.strip().split())

    @field_validator("origin_text", "destination_text")
    @classmethod
    def validate_location(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("Route locations cannot be empty.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None


class SavedRouteCreate(SavedRouteInput):
    pass


class SavedRouteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    origin_text: str | None = Field(default=None, min_length=1, max_length=255)
    destination_text: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    sms_enabled: bool | None = None
    web_enabled: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=10_000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return SavedRouteInput.validate_name(value) if value is not None else None

    @field_validator("origin_text", "destination_text")
    @classmethod
    def validate_location(cls, value: str | None) -> str | None:
        return SavedRouteInput.validate_location(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return SavedRouteInput.normalize_description(value)


class SavedRouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    normalized_name: str
    origin_text: str
    destination_text: str
    description: str | None
    is_active: bool
    sms_enabled: bool
    web_enabled: bool
    sort_order: int
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SavedRouteListResponse(BaseModel):
    routes: list[SavedRouteResponse]
