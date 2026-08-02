import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _runtime_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    return Path(raw).expanduser().resolve() if raw else default.resolve()


DATA_DIR = _runtime_path("DATA_DIR", BACKEND_DIR / "data")
UPLOAD_DIR = _runtime_path("UPLOAD_DIR", DATA_DIR / "uploads")
CERTIFICATE_DIR = _runtime_path("CERTIFICATE_DIR", DATA_DIR / "certificates")
REPORT_DIR = _runtime_path("REPORT_DIR", DATA_DIR / "reports")
INVOICE_DIR = _runtime_path("INVOICE_DIR", DATA_DIR / "invoices")
RECEIPT_DIR = _runtime_path("RECEIPT_DIR", DATA_DIR / "receipts")
BACKUP_DIR = _runtime_path("BACKUP_DIR", DATA_DIR / "backups")
LOG_DIR = _runtime_path("LOG_DIR", DATA_DIR / "logs")
EXPORT_DIR = _runtime_path("EXPORT_DIR", DATA_DIR / "exports")
MAP_DIR = _runtime_path("MAP_DIR", DATA_DIR / "maps")
MAP_CACHE_DIR = _runtime_path("MAP_CACHE_DIR", DATA_DIR / "map-cache")
TEMP_DIR = _runtime_path("TEMP_DIR", DATA_DIR / "temp")
ATTACHMENT_DIR = _runtime_path("ATTACHMENT_DIR", DATA_DIR / "attachments")
SIGNATURE_DIR = _runtime_path("SIGNATURE_DIR", UPLOAD_DIR / "signatures")


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.expanduser().resolve().as_posix()}"


for _directory in (
    DATA_DIR,
    UPLOAD_DIR,
    CERTIFICATE_DIR,
    REPORT_DIR,
    INVOICE_DIR,
    RECEIPT_DIR,
    BACKUP_DIR,
    LOG_DIR,
    EXPORT_DIR,
    MAP_DIR,
    MAP_CACHE_DIR,
    TEMP_DIR,
    ATTACHMENT_DIR,
    SIGNATURE_DIR,
):
    _directory.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    app_name: str = "FNLIFTING Enterprise ERP"
    app_version: str = "0.12.1"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-this-key-before-production-7f58b4d2"
    algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    database_url: str = sqlite_url(DATA_DIR / "fnlifting.db")
    data_dir: str = str(DATA_DIR)
    upload_dir: str = str(UPLOAD_DIR)
    certificate_dir: str = str(CERTIFICATE_DIR)
    report_dir: str = str(REPORT_DIR)
    invoice_dir: str = str(INVOICE_DIR)
    receipt_dir: str = str(RECEIPT_DIR)
    backup_dir: str = str(BACKUP_DIR)
    log_dir: str = str(LOG_DIR)
    export_dir: str = str(EXPORT_DIR)
    map_dir: str = str(MAP_DIR)
    map_cache_dir: str = str(MAP_CACHE_DIR)
    temp_dir: str = str(TEMP_DIR)
    attachment_dir: str = str(ATTACHMENT_DIR)
    signature_dir: str = str(SIGNATURE_DIR)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    sync_remote_url: str = ""
    backup_encryption_key: str = ""
    storage_provider: str = "LOCAL"
    storage_bucket: str = "fnlifting"
    storage_endpoint_url: str = ""
    storage_region: str = "us-east-1"
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_secure: bool = True
    storage_public_base_url: str = ""
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
        return sqlite_url(BACKEND_DIR / relative)
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
        data_dir=str(DATA_DIR),
        upload_dir=str(UPLOAD_DIR),
        certificate_dir=str(CERTIFICATE_DIR),
        report_dir=str(REPORT_DIR),
        invoice_dir=str(INVOICE_DIR),
        receipt_dir=str(RECEIPT_DIR),
        backup_dir=str(BACKUP_DIR),
        log_dir=str(LOG_DIR),
        export_dir=str(EXPORT_DIR),
        map_dir=str(MAP_DIR),
        map_cache_dir=str(MAP_CACHE_DIR),
        temp_dir=str(TEMP_DIR),
        attachment_dir=str(ATTACHMENT_DIR),
        signature_dir=str(SIGNATURE_DIR),
        cors_origins=os.getenv("CORS_ORIGINS", defaults.cors_origins),
        sync_remote_url=os.getenv("SYNC_REMOTE_URL", defaults.sync_remote_url),
        backup_encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY", defaults.backup_encryption_key),
        storage_provider=os.getenv("STORAGE_PROVIDER", defaults.storage_provider).upper(),
        storage_bucket=os.getenv("STORAGE_BUCKET", defaults.storage_bucket),
        storage_endpoint_url=os.getenv("STORAGE_ENDPOINT_URL", defaults.storage_endpoint_url),
        storage_region=os.getenv("STORAGE_REGION", defaults.storage_region),
        storage_access_key_id=os.getenv("STORAGE_ACCESS_KEY_ID", defaults.storage_access_key_id),
        storage_secret_access_key=os.getenv("STORAGE_SECRET_ACCESS_KEY", defaults.storage_secret_access_key),
        storage_secure=_bool_env("STORAGE_SECURE", defaults.storage_secure),
        storage_public_base_url=os.getenv("STORAGE_PUBLIC_BASE_URL", defaults.storage_public_base_url),
        allowed_hosts=os.getenv("ALLOWED_HOSTS", defaults.allowed_hosts),
        auto_create_schema=_bool_env("AUTO_CREATE_SCHEMA", defaults.auto_create_schema),
        security_headers_enabled=_bool_env("SECURITY_HEADERS_ENABLED", defaults.security_headers_enabled),
        backup_warning_hours=int(os.getenv("BACKUP_WARNING_HOURS", defaults.backup_warning_hours)),
    )


settings = get_settings()
