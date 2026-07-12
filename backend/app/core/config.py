import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    app_name: str = "FNLIFTING Enterprise ERP"
    app_version: str = "0.12.0"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-this-key-before-production-7f58b4d2"
    algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    database_url: str = f"sqlite:///{(DATA_DIR / 'fnlifting.db').as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    sync_remote_url: str = ""
    backup_encryption_key: str = ""
    allowed_hosts: str = "localhost,127.0.0.1"
    auto_create_schema: bool = True
    security_headers_enabled: bool = True
    backup_warning_hours: int = 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _database_url(value: str) -> str:
    if value.startswith("sqlite:///./"):
        relative = value.removeprefix("sqlite:///./")
        return f"sqlite:///{(BACKEND_DIR / relative).as_posix()}"
    return value


@lru_cache
def get_settings() -> Settings:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    defaults = Settings()
    return Settings(
        app_name=os.getenv("APP_NAME", defaults.app_name),
        app_version=os.getenv("APP_VERSION", defaults.app_version),
        environment=os.getenv("ENVIRONMENT", defaults.environment),
        debug=_bool_env("DEBUG", defaults.debug),
        api_v1_prefix=os.getenv("API_V1_PREFIX", defaults.api_v1_prefix),
        secret_key=os.getenv("SECRET_KEY", defaults.secret_key),
        algorithm=os.getenv("ALGORITHM", defaults.algorithm),
        access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", defaults.access_token_minutes)),
        refresh_token_days=int(os.getenv("REFRESH_TOKEN_DAYS", defaults.refresh_token_days)),
        database_url=_database_url(os.getenv("DATABASE_URL", defaults.database_url)),
        cors_origins=os.getenv("CORS_ORIGINS", defaults.cors_origins),
        sync_remote_url=os.getenv("SYNC_REMOTE_URL", defaults.sync_remote_url),
        backup_encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY", defaults.backup_encryption_key),
        allowed_hosts=os.getenv("ALLOWED_HOSTS", defaults.allowed_hosts),
        auto_create_schema=_bool_env("AUTO_CREATE_SCHEMA", defaults.auto_create_schema),
        security_headers_enabled=_bool_env("SECURITY_HEADERS_ENABLED", defaults.security_headers_enabled),
        backup_warning_hours=int(os.getenv("BACKUP_WARNING_HOURS", defaults.backup_warning_hours)),
    )


settings = get_settings()
