from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    TokenExpiredError,
    UserAlreadyExistsError,
)
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    AuthenticationResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.auth.service import AuthService
from app.core.database import get_db
from app.models.entities import User

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


def get_auth_service(
    db: Session = Depends(get_db),
) -> AuthService:
    return AuthService(AuthRepository(db))


def get_request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_request_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.register(body)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=AuthenticationResponse,
)
def login(
    body: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.login(
            identifier=body.identifier,
            password=body.password,
            ip_address=get_request_ip(request),
            user_agent=get_request_user_agent(request),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except EmailNotVerifiedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        ) from exc
    except AccountDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(
    body: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.refresh(
            refresh_token=body.refresh_token,
            ip_address=get_request_ip(request),
            user_agent=get_request_user_agent(request),
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        ) from exc
    except AccountDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    body: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.logout(
        refresh_token=body.refresh_token,
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email(
    body: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.verify_email(token=body.token)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    body: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.forgot_password(email=body.email)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def reset_password(
    body: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.reset_password(
            token=body.token,
            new_password=body.new_password,
        )
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/me",
    response_model=dict,
)
def me(
    current_user: User = Depends(get_current_active_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "phone_number": current_user.phone_e164,
        "email_verified": current_user.email_verified,
        "subscription_status": current_user.subscription_status,
        "subscription_plan": current_user.subscription_plan,
    }
