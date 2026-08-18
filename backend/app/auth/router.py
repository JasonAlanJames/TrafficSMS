from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_active_user,
    get_current_session_id,
)
from app.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    AuthenticationError,
    AuthenticationRateLimitError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    PasswordReuseError,
    TokenExpiredError,
    UserAlreadyExistsError,
)
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    AuthenticationResponse,
    AuthenticatedUser,
    ForgotPasswordRequest,
    LogoutRequest,
    MessageResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionInfoResponse,
    TokenResponse,
    VerifyEmailRequest,
    ConfirmEmailChangeRequest,
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

    if isinstance(exc, InvalidRefreshTokenError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    if isinstance(exc, EmailNotVerifiedError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, AccountDisabledError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, AccountLockedError):
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds is not None
            else None
        )
        return HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
            headers=headers,
        )

    if isinstance(exc, AuthenticationRateLimitError):
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds is not None
            else None
        )
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=headers,
        )

    if isinstance(exc, TokenExpiredError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(exc, InvalidTokenError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(exc, PasswordReuseError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(exc, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    raise exc


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
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


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
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


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
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    body: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.logout(
            refresh_token=body.refresh_token,
        )
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.post(
    "/logout-all",
    response_model=MessageResponse,
)
def logout_all(
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.logout_all(user=current_user)
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.get(
    "/sessions",
    response_model=list[SessionInfoResponse],
)
def list_sessions(
    current_user: User = Depends(get_current_active_user),
    current_session_id: UUID | None = Depends(get_current_session_id),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.list_sessions(
            user=current_user,
            current_session_id=current_session_id,
        )
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
)
def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.revoke_session(
            user=current_user,
            session_id=session_id,
        )
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


def _verify_email_token(
    *,
    token: str,
    service: AuthService,
) -> MessageResponse:
    try:
        return service.verify_email(token=token)
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.get(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email(
    token: str,
    service: AuthService = Depends(get_auth_service),
):
    return _verify_email_token(token=token, service=service)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email_post(
    body: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
):
    return _verify_email_token(token=body.token, service=service)


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
)
def resend_verification(
    body: ResendVerificationRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.resend_verification(email=body.email)
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    body: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.forgot_password(email=body.email)
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


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
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.post(
    "/confirm-email-change",
    response_model=MessageResponse,
)
def confirm_email_change(
    body: ConfirmEmailChangeRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.confirm_email_change(token=body.token)
    except Exception as exc:
        raise _translate_auth_error(exc) from exc


@router.get(
    "/me",
    response_model=AuthenticatedUser,
)
def me(
    current_user: User = Depends(get_current_active_user),
):
    return AuthenticatedUser.model_validate(current_user)
