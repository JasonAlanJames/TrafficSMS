from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


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
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthenticationResponse(BaseModel):
    user: AuthenticatedUser
    tokens: TokenResponse


class RegisterResponse(BaseModel):
    message: str
    email_verification_sent: bool = True


class MessageResponse(BaseModel):
    message: str
