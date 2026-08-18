from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    AuthenticationError,
    InvalidCredentialsError,
    PasswordReuseError,
    UserAlreadyExistsError,
)
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    AuthenticatedUser,
    ChangeEmailRequest,
    ChangePasswordRequest,
    ChangePhoneRequest,
    MessageResponse,
    UpdateProfileRequest,
)
from app.auth.service import AuthService
from app.core.database import get_db
from app.models.entities import User

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


def get_auth_service(
    db: Session = Depends(get_db),
) -> AuthService:
    return AuthService(AuthRepository(db))


def _translate_auth_error(exc: Exception) -> HTTPException:
    if isinstance(exc, UserAlreadyExistsError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if isinstance(exc, InvalidCredentialsError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    if isinstance(exc, PasswordReuseError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(exc, AccountLockedError):
        return HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        )

    if isinstance(exc, AccountDisabledError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    raise exc


@router.get(
    "/me",
    response_model=AuthenticatedUser,
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    return AuthenticatedUser.model_validate(current_user)


@router.patch(
    "/me",
    response_model=AuthenticatedUser,
)
def update_current_user_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        updated = service.update_profile(
            user=current_user,
            request=body,
        )
        return AuthenticatedUser.model_validate(updated)
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.change_password(
            user=current_user,
            request=body,
        )
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.post(
    "/me/change-email",
    response_model=MessageResponse,
)
def change_email(
    body: ChangeEmailRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.request_email_change(
            user=current_user,
            request=body,
        )
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.post(
    "/me/change-phone",
    response_model=AuthenticatedUser,
)
def change_phone(
    body: ChangePhoneRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.change_phone(
            user=current_user,
            request=body,
        )
    except Exception as exc:
        raise _translate_auth_error(exc) from exc
