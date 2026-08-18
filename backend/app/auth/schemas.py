from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

E164_US_PATTERN = re.compile(r"^\+1\d{10}$")


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain an uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain a lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain a number.")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must contain a special character.")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone_number: str
    sms_consent: bool
    marketing_consent: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        if not E164_US_PATTERN.fullmatch(value):
            raise ValueError("Phone number must be a valid US E.164 value.")
        return value

    @field_validator("sms_consent")
    @classmethod
    def require_sms_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("SMS consent is required.")
        return value


class LoginRequest(BaseModel):
    identifier: str = Field(
        min_length=3,
        max_length=320,
        validation_alias=AliasChoices("identifier", "email"),
    )
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    phone_e164: str | None
    subscription_status: str
    subscription_plan: str | None
    email_verified: bool
    phone_verified: bool
    is_active: bool
    home_location: str | None
    work_location: str | None
    gym_location: str | None
    school_location: str | None
    default_state: str | None
    default_country: str
    pending_email: EmailStr | None
    phone_verification_requested_at: datetime | None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class AuthenticationResponse(TokenResponse):
    user: AuthenticatedUser


class RegisterResponse(BaseModel):
    message: str
    email_verification_sent: bool = True


class MessageResponse(BaseModel):
    message: str


class UpdateProfileRequest(BaseModel):
    home_location: str | None = Field(default=None, max_length=255)
    work_location: str | None = Field(default=None, max_length=255)
    gym_location: str | None = Field(default=None, max_length=255)
    school_location: str | None = Field(default=None, max_length=255)
    default_state: str | None = Field(default=None, min_length=2, max_length=2)
    default_country: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator(
        "home_location",
        "work_location",
        "gym_location",
        "school_location",
    )
    @classmethod
    def normalize_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("default_state", "default_country")
    @classmethod
    def normalize_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str = Field(min_length=8, max_length=128)


class ConfirmEmailChangeRequest(BaseModel):
    token: str


class ChangePhoneRequest(BaseModel):
    phone_number: str
    current_password: str = Field(min_length=8, max_length=128)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        if not E164_US_PATTERN.fullmatch(value):
            raise ValueError("Phone number must be a valid US E.164 value.")
        return value


class SessionInfoResponse(BaseModel):
    id: UUID
    ip_address: str | None
    user_agent: str | None
    device_name: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    is_current: bool
