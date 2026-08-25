from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "法规变更情报与影响研判平台"
    api_prefix: str = "/api"

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/fagui"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Crawler
    snapshot_dir: str = "/data/snapshots"
    user_agent: str = "FaguiIntelBot/1.0 (+compliance-monitor)"
    request_timeout: int = 20
    respect_robots: bool = True

    # Auth (lightweight, demo purpose)
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 720
    admin_password: str = "admin123"
    analyst_password: str = "analyst123"

    # Email / SMTP notifications
    smtp_host: str = ""            # empty -> email delivery disabled (logged only)
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from: str = "fagui-intel@example.com"
    notify_email_to: str = ""      # default recipient when a subscription has no explicit address


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
