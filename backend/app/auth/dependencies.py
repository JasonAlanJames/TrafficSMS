from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.repository import AuthRepository
from app.auth.security import decode_access_token
from app.core.database import get_db
from app.models.entities import User

bearer_scheme = HTTPBearer(auto_error=True)


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Security(
        bearer_scheme,
    ),
) -> dict:
    return decode_access_token(credentials.credentials)


def get_current_session_id(
    payload: dict = Depends(get_current_token_payload),
) -> UUID | None:
    raw_session_id = payload.get("session_id")

    if not raw_session_id:
        return None

    try:
        return UUID(str(raw_session_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc


def get_current_user(
    payload: dict = Depends(get_current_token_payload),
    current_session_id: UUID | None = Depends(get_current_session_id),
    db: Session = Depends(get_db),
) -> User:
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    repository = AuthRepository(db)
    user = repository.get_by_id(int(user_id))
    now = datetime.now(UTC)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    token_version = int(payload.get("token_version", 0) or 0)
    if token_version != user.session_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer active.",
        )

    if current_session_id is not None:
        session = repository.get_refresh_token_for_user(
            user_id=user.id,
            token_id=current_session_id,
        )
        session_expires_at = _as_utc(session.expires_at) if session else None

        if (
            session is None
            or session.revoked
            or (session_expires_at is not None and session_expires_at <= now)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session is no longer active.",
            )

    return user


def get_current_active_user(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    repository = AuthRepository(db)
    now = datetime.now(UTC)
    locked_until = _as_utc(user.locked_until)

    if user.is_locked and locked_until is not None and locked_until <= now:
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        repository.save(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    if user.is_locked:
        retry_after_seconds = None
        if locked_until is not None and locked_until > now:
            retry_after_seconds = int(
                max((locked_until - now).total_seconds(), 1)
            )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked.",
            headers=(
                {"Retry-After": str(retry_after_seconds)}
                if retry_after_seconds is not None
                else None
            ),
        )

    return user
