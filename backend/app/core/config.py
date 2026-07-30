from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------

    app_env: str = "development"
    public_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    # -------------------------------------------------------------------------
    # Twilio
    # -------------------------------------------------------------------------

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    # -------------------------------------------------------------------------
    # Stripe
    # -------------------------------------------------------------------------

    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: str

    stripe_standard_monthly_product_id: str
    stripe_standard_monthly_price_id: str

    stripe_unlimited_monthly_product_id: str
    stripe_unlimited_monthly_price_id: str

    # -------------------------------------------------------------------------
    # Traffic Cache
    # -------------------------------------------------------------------------

    traffic_cache_ttl_seconds: int = 90
    traffic_cache_stale_seconds: int = 900
    traffic_cache_lock_seconds: int = 15

    # -------------------------------------------------------------------------
    # Pydantic Settings
    # -------------------------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
