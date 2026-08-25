from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """全局配置，环境变量同名覆盖（大小写不敏感）。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/regintel"
    redis_url: str = "redis://localhost:6379/0"
    snapshot_dir: str = str(_BACKEND_DIR / "data" / "snapshots")
    crawl_user_agent: str = "RegIntelBot/1.0 (+https://example.org/regintel)"
    max_attachment_bytes: int = 20 * 1024 * 1024
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = ""
    # 首次播种 admin 的初始密码，留空则用 admin123
    admin_initial_password: str = ""


settings = Settings()
