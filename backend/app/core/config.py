from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def derive_async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace(
            "postgresql+psycopg://",
            "postgresql+asyncpg://",
            1,
        )

    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    return database_url


class Settings(BaseSettings):
    app_name: str = Field(
        default="TrafficSMS",
        validation_alias=AliasChoices("APP_NAME", "app_name"),
    )
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "app_env"),
    )
    public_base_url: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("PUBLIC_BASE_URL", "public_base_url"),
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("FRONTEND_URL", "frontend_url"),
    )

    database_url: str = Field(
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "DATABASE_SYNC_URL",
            "database_url",
        ),
    )
    database_async_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_ASYNC_URL",
            "database_async_url",
        ),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )

    secret_key: str = Field(
        default="replace_me",
        validation_alias=AliasChoices("SECRET_KEY", "secret_key"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "jwt_algorithm"),
    )
    access_token_expire_minutes: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "access_token_expire_minutes",
        ),
    )
    refresh_token_expire_days: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "REFRESH_TOKEN_EXPIRE_DAYS",
            "refresh_token_expire_days",
        ),
    )
    email_verification_token_expire_hours: int = Field(
        default=48,
        validation_alias=AliasChoices(
            "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS",
            "email_verification_token_expire_hours",
        ),
    )
    password_reset_token_expire_hours: int = Field(
        default=1,
        validation_alias=AliasChoices(
            "PASSWORD_RESET_TOKEN_EXPIRE_HOURS",
            "password_reset_token_expire_hours",
        ),
    )
    failed_login_lockout_threshold: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "FAILED_LOGIN_LOCKOUT_THRESHOLD",
            "failed_login_lockout_threshold",
        ),
    )

    twilio_account_sid: str = Field(
        default="",
        validation_alias=AliasChoices(
            "TWILIO_ACCOUNT_SID",
            "twilio_account_sid",
        ),
    )
    twilio_auth_token: str = Field(
        default="",
        validation_alias=AliasChoices(
            "TWILIO_AUTH_TOKEN",
            "twilio_auth_token",
        ),
    )
    twilio_phone_number: str = Field(
        default="",
        validation_alias=AliasChoices(
            "TWILIO_PHONE_NUMBER",
            "twilio_phone_number",
        ),
    )

    stripe_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "STRIPE_SECRET_KEY",
            "stripe_secret_key",
        ),
    )
    stripe_publishable_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "STRIPE_PUBLISHABLE_KEY",
            "stripe_publishable_key",
        ),
    )
    stripe_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "STRIPE_WEBHOOK_SECRET",
            "stripe_webhook_secret",
        ),
    )
    stripe_standard_monthly_product_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "STRIPE_STANDARD_MONTHLY_PRODUCT_ID",
            "stripe_standard_monthly_product_id",
        ),
    )
    stripe_standard_monthly_price_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "STRIPE_STANDARD_MONTHLY_PRICE_ID",
            "stripe_standard_monthly_price_id",
        ),
    )
    stripe_unlimited_monthly_product_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "STRIPE_UNLIMITED_MONTHLY_PRODUCT_ID",
            "stripe_unlimited_monthly_product_id",
        ),
    )
    stripe_unlimited_monthly_price_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "STRIPE_UNLIMITED_MONTHLY_PRICE_ID",
            "stripe_unlimited_monthly_price_id",
        ),
    )

    google_maps_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GOOGLE_MAPS_API_KEY",
            "google_maps_api_key",
        ),
    )
    google_maps_timeout_seconds: int = Field(
        default=10,
        validation_alias=AliasChoices(
            "GOOGLE_MAPS_TIMEOUT_SECONDS",
            "google_maps_timeout_seconds",
        ),
    )

    traffic_cache_ttl_seconds: int = Field(
        default=90,
        validation_alias=AliasChoices(
            "TRAFFIC_CACHE_TTL_SECONDS",
            "traffic_cache_ttl_seconds",
        ),
    )
    traffic_cache_stale_seconds: int = Field(
        default=900,
        validation_alias=AliasChoices(
            "TRAFFIC_CACHE_STALE_SECONDS",
            "traffic_cache_stale_seconds",
        ),
    )
    traffic_cache_lock_seconds: int = Field(
        default=15,
        validation_alias=AliasChoices(
            "TRAFFIC_CACHE_LOCK_SECONDS",
            "traffic_cache_lock_seconds",
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def APP_NAME(self) -> str:
        return self.app_name

    @property
    def APP_ENV(self) -> str:
        return self.app_env

    @property
    def FRONTEND_URL(self) -> str:
        return self.frontend_url

    @property
    def PUBLIC_BASE_URL(self) -> str:
        return self.public_base_url

    @property
    def DATABASE_SYNC_URL(self) -> str:
        return self.database_url

    @property
    def DATABASE_ASYNC_URL(self) -> str:
        return self.database_async_url or derive_async_database_url(
            self.database_url
        )

    @property
    def SECRET_KEY(self) -> str:
        return self.secret_key

    @property
    def JWT_ALGORITHM(self) -> str:
        return self.jwt_algorithm

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.access_token_expire_minutes

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        return self.refresh_token_expire_days

    @property
    def STRIPE_SECRET_KEY(self) -> str:
        return self.stripe_secret_key

    @property
    def STRIPE_WEBHOOK_SECRET(self) -> str:
        return self.stripe_webhook_secret

    @property
    def STRIPE_STANDARD_MONTHLY_PRODUCT_ID(self) -> str:
        return self.stripe_standard_monthly_product_id

    @property
    def STRIPE_STANDARD_MONTHLY_PRICE_ID(self) -> str:
        return self.stripe_standard_monthly_price_id

    @property
    def STRIPE_UNLIMITED_MONTHLY_PRODUCT_ID(self) -> str:
        return self.stripe_unlimited_monthly_product_id

    @property
    def STRIPE_UNLIMITED_MONTHLY_PRICE_ID(self) -> str:
        return self.stripe_unlimited_monthly_price_id

    @property
    def TWILIO_AUTH_TOKEN(self) -> str:
        return self.twilio_auth_token

    @property
    def TWILIO_PHONE_NUMBER(self) -> str:
        return self.twilio_phone_number


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
