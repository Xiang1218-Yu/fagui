from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "法规变更情报与影响研判平台"

    database_url: str = "postgresql+psycopg://fagui:fagui@localhost:5432/fagui"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    crawl_eager: bool = False

    storage_dir: str = "data/storage"
    demo_site_dir: str = "data/demo_site"

    jwt_secret: str = "fagui-intel-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    user_agent: str = "FaguiIntelBot/1.0 (+regulatory-change-intelligence; compliance-research)"
    crawl_timeout: float = 20.0
    crawl_max_pages: int = 60
    crawl_default_max_depth: int = 2
    crawl_politeness_delay: float = 0.8

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
