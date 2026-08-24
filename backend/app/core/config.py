from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
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
    email_verification_resend_cooldown_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS",
            "email_verification_resend_cooldown_seconds",
        ),
    )
    password_reset_token_expire_hours: int = Field(
        default=1,
        validation_alias=AliasChoices(
            "PASSWORD_RESET_TOKEN_EXPIRE_HOURS",
            "password_reset_token_expire_hours",
        ),
    )
    password_reset_resend_cooldown_seconds: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "PASSWORD_RESET_RESEND_COOLDOWN_SECONDS",
            "password_reset_resend_cooldown_seconds",
        ),
    )
    failed_login_lockout_threshold: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "FAILED_LOGIN_LOCKOUT_THRESHOLD",
            "failed_login_lockout_threshold",
        ),
    )
    failed_login_window_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices(
            "FAILED_LOGIN_WINDOW_MINUTES",
            "failed_login_window_minutes",
        ),
    )
    failed_login_rate_limit_attempts: int = Field(
        default=10,
        validation_alias=AliasChoices(
            "FAILED_LOGIN_RATE_LIMIT_ATTEMPTS",
            "failed_login_rate_limit_attempts",
        ),
    )
    account_lockout_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices(
            "ACCOUNT_LOCKOUT_MINUTES",
            "account_lockout_minutes",
        ),
    )
    refresh_token_retention_days: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "REFRESH_TOKEN_RETENTION_DAYS",
            "refresh_token_retention_days",
        ),
    )

    smtp_host: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_HOST", "smtp_host"),
    )
    smtp_port: int = Field(
        default=0,
        validation_alias=AliasChoices("SMTP_PORT", "smtp_port"),
    )
    smtp_username: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_USERNAME", "smtp_username"),
    )
    smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_PASSWORD", "smtp_password"),
    )
    smtp_tls: bool = Field(
        default=False,
        validation_alias=AliasChoices("SMTP_TLS", "smtp_tls"),
    )
    smtp_ssl: bool = Field(
        default=False,
        validation_alias=AliasChoices("SMTP_SSL", "smtp_ssl"),
    )
    mail_from: str = Field(
        default="",
        validation_alias=AliasChoices("MAIL_FROM", "mail_from"),
    )
    mail_from_name: str = Field(
        default="",
        validation_alias=AliasChoices("MAIL_FROM_NAME", "mail_from_name"),
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
    stripe_portal_return_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "STRIPE_PORTAL_RETURN_URL",
            "stripe_portal_return_url",
        ),
    )
    admin_emails: str = Field(
        default="",
        validation_alias=AliasChoices(
            "ADMIN_EMAILS",
            "admin_emails",
        ),
    )
    billing_grace_period_days: int = Field(
        default=3,
        validation_alias=AliasChoices(
            "BILLING_GRACE_PERIOD_DAYS",
            "billing_grace_period_days",
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
    llm_intent_confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "LLM_INTENT_CONFIDENCE_THRESHOLD",
            "llm_intent_confidence_threshold",
        ),
    )
    sms_conversation_ttl_seconds: int = Field(
        default=600,
        ge=1,
        validation_alias=AliasChoices(
            "SMS_CONVERSATION_TTL_SECONDS",
            "sms_conversation_ttl_seconds",
        ),
    )
    typo_correction_max_edit_distance: int = Field(
        default=2,
        ge=0,
        validation_alias=AliasChoices(
            "TYPO_CORRECTION_MAX_EDIT_DISTANCE",
            "typo_correction_max_edit_distance",
        ),
    )
    typo_correction_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "TYPO_CORRECTION_THRESHOLD",
            "typo_correction_threshold",
        ),
    )
    bedrock_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("BEDROCK_ENABLED", "bedrock_enabled"),
    )
    bedrock_region: str = Field(
        default="us-west-2",
        validation_alias=AliasChoices("BEDROCK_REGION", "bedrock_region"),
    )
    bedrock_model_id: str = Field(
        default="amazon.nova-lite-v1:0",
        validation_alias=AliasChoices("BEDROCK_MODEL_ID", "bedrock_model_id"),
    )
    bedrock_timeout_seconds: int = Field(
        default=3,
        ge=1,
        validation_alias=AliasChoices(
            "BEDROCK_TIMEOUT_SECONDS", "bedrock_timeout_seconds"
        ),
    )
    bedrock_retry_count: int = Field(
        default=1,
        ge=0,
        validation_alias=AliasChoices("BEDROCK_RETRY_COUNT", "bedrock_retry_count"),
    )
    bedrock_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("BEDROCK_TEMPERATURE", "bedrock_temperature"),
    )
    bedrock_max_tokens: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices("BEDROCK_MAX_TOKENS", "bedrock_max_tokens"),
    )
    bedrock_top_p: float = Field(
        default=0.9,
        gt=0.0,
        le=1.0,
        validation_alias=AliasChoices("BEDROCK_TOP_P", "bedrock_top_p"),
    )
    ai_summary_max_input_incidents: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices("AI_SUMMARY_MAX_INPUT_INCIDENTS", "ai_summary_max_input_incidents"),
    )
    ai_summary_max_output_chars: int = Field(
        default=320,
        ge=1,
        validation_alias=AliasChoices("AI_SUMMARY_MAX_OUTPUT_CHARS", "ai_summary_max_output_chars"),
    )
    sms_character_threshold: int = Field(
        default=160,
        ge=1,
        validation_alias=AliasChoices(
            "SMS_CHARACTER_THRESHOLD", "sms_character_threshold"
        ),
    )
    mms_character_threshold: int = Field(
        default=1600,
        ge=1,
        validation_alias=AliasChoices(
            "MMS_CHARACTER_THRESHOLD", "mms_character_threshold"
        ),
    )
    delivery_compression_threshold: int = Field(
        default=320,
        ge=1,
        validation_alias=AliasChoices(
            "DELIVERY_COMPRESSION_THRESHOLD", "delivery_compression_threshold"
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_environment_secrets(self) -> "Settings":
        """
        Prevent production Stripe credentials from being used accidentally
        by local development or automated test environments.

        This guard exists specifically to ensure that local authentication
        and billing tests cannot create real Stripe customers, charges,
        subscriptions, or other live-mode Stripe resources.
        """
        environment = (self.app_env or "").strip().lower()
        stripe_key = (self.stripe_secret_key or "").strip()

        non_production_environments = {
            "development",
            "dev",
            "test",
            "testing",
            "local",
        }

        if (
            environment in non_production_environments
            and stripe_key.startswith("sk_live_")
        ):
            raise ValueError(
                "SECURITY BLOCK: TrafficSMS refuses to use a live Stripe "
                "secret key when APP_ENV is development, dev, test, testing, "
                "or local. Use a Stripe test-mode key (sk_test_...) or leave "
                "STRIPE_SECRET_KEY empty."
            )

        return self

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
    def EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS(self) -> int:
        return self.email_verification_resend_cooldown_seconds

    @property
    def PASSWORD_RESET_RESEND_COOLDOWN_SECONDS(self) -> int:
        return self.password_reset_resend_cooldown_seconds

    @property
    def FAILED_LOGIN_WINDOW_MINUTES(self) -> int:
        return self.failed_login_window_minutes

    @property
    def FAILED_LOGIN_RATE_LIMIT_ATTEMPTS(self) -> int:
        return self.failed_login_rate_limit_attempts

    @property
    def ACCOUNT_LOCKOUT_MINUTES(self) -> int:
        return self.account_lockout_minutes

    @property
    def REFRESH_TOKEN_RETENTION_DAYS(self) -> int:
        return self.refresh_token_retention_days

    @property
    def SMTP_HOST(self) -> str:
        return self.smtp_host

    @property
    def SMTP_PORT(self) -> int:
        return self.smtp_port

    @property
    def SMTP_USERNAME(self) -> str:
        return self.smtp_username

    @property
    def SMTP_PASSWORD(self) -> str:
        return self.smtp_password

    @property
    def SMTP_TLS(self) -> bool:
        return self.smtp_tls

    @property
    def SMTP_SSL(self) -> bool:
        return self.smtp_ssl

    @property
    def MAIL_FROM(self) -> str:
        return self.mail_from

    @property
    def MAIL_FROM_NAME(self) -> str:
        return self.mail_from_name

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
    def STRIPE_PORTAL_RETURN_URL(self) -> str:
        return (
            self.stripe_portal_return_url
            or f"{self.frontend_url.rstrip('/')}/dashboard"
        )

    @property
    def ADMIN_EMAILS(self) -> list[str]:
        return [
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        ]

    @property
    def BILLING_GRACE_PERIOD_DAYS(self) -> int:
        return self.billing_grace_period_days

    @property
    def LLM_INTENT_CONFIDENCE_THRESHOLD(self) -> float:
        return self.llm_intent_confidence_threshold

    @property
    def SMS_CONVERSATION_TTL_SECONDS(self) -> int:
        return self.sms_conversation_ttl_seconds

    @property
    def TYPO_CORRECTION_MAX_EDIT_DISTANCE(self) -> int:
        return self.typo_correction_max_edit_distance

    @property
    def TYPO_CORRECTION_THRESHOLD(self) -> float:
        return self.typo_correction_threshold

    @property
    def BEDROCK_ENABLED(self) -> bool:
        return self.bedrock_enabled

    @property
    def BEDROCK_REGION(self) -> str:
        return self.bedrock_region

    @property
    def BEDROCK_MODEL_ID(self) -> str:
        return self.bedrock_model_id

    @property
    def BEDROCK_TIMEOUT_SECONDS(self) -> int:
        return self.bedrock_timeout_seconds

    @property
    def BEDROCK_RETRY_COUNT(self) -> int:
        return self.bedrock_retry_count

    @property
    def BEDROCK_TEMPERATURE(self) -> float:
        return self.bedrock_temperature

    @property
    def BEDROCK_MAX_TOKENS(self) -> int:
        return self.bedrock_max_tokens

    @property
    def BEDROCK_TOP_P(self) -> float:
        return self.bedrock_top_p

    @property
    def SMS_CHARACTER_THRESHOLD(self) -> int:
        return self.sms_character_threshold

    @property
    def MMS_CHARACTER_THRESHOLD(self) -> int:
        return self.mms_character_threshold

    @property
    def DELIVERY_COMPRESSION_THRESHOLD(self) -> int:
        return self.delivery_compression_threshold

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
