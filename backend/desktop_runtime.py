from __future__ import annotations

import argparse
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config


APP_NAME = "FNLIFTING Enterprise ERP"


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()


def env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    return Path(raw).expanduser().resolve() if raw else default.expanduser().resolve()


def configure_logging() -> Path:
    data_dir = env_path("DATA_DIR", Path.cwd() / "data")
    log_dir = env_path("LOG_DIR", data_dir / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "backend-standalone.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )
    return log_file


def prepare_runtime_dirs() -> dict[str, Path]:
    data_dir = env_path("DATA_DIR", Path.cwd() / "data")
    dirs = {
        "DATA_DIR": data_dir,
        "UPLOAD_DIR": env_path("UPLOAD_DIR", data_dir / "uploads"),
        "CERTIFICATE_DIR": env_path("CERTIFICATE_DIR", data_dir / "certificates"),
        "REPORT_DIR": env_path("REPORT_DIR", data_dir / "reports"),
        "INVOICE_DIR": env_path("INVOICE_DIR", data_dir / "invoices"),
        "RECEIPT_DIR": env_path("RECEIPT_DIR", data_dir / "receipts"),
        "BACKUP_DIR": env_path("BACKUP_DIR", data_dir / "backups"),
        "LOG_DIR": env_path("LOG_DIR", data_dir / "logs"),
        "EXPORT_DIR": env_path("EXPORT_DIR", data_dir / "exports"),
        "MAP_DIR": env_path("MAP_DIR", data_dir / "maps"),
        "MAP_CACHE_DIR": env_path("MAP_CACHE_DIR", data_dir / "map-cache"),
        "TEMP_DIR": env_path("TEMP_DIR", data_dir / "temp"),
        "ATTACHMENT_DIR": env_path("ATTACHMENT_DIR", data_dir / "attachments"),
    }
    for name, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = f"sqlite:///{(data_dir / 'fnlifting.db').resolve().as_posix()}"
    os.environ.setdefault("ENVIRONMENT", os.getenv("APP_ENV", "desktop"))
    os.environ.setdefault("APP_ENV", "desktop")
    os.environ.setdefault("DESKTOP_MODE", "true")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("AUTO_CREATE_SCHEMA", "true")
    os.environ.setdefault("SECURITY_HEADERS_ENABLED", "true")
    return dirs


def sqlite_database_path() -> Path | None:
    from app.core.config import settings

    if not settings.database_url.startswith("sqlite"):
        return None
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    return Path(url.database).expanduser().resolve() if url.database else None


def ensure_sqlite_access() -> None:
    database = sqlite_database_path()
    if not database:
        return
    database.parent.mkdir(parents=True, exist_ok=True)
    probe = database.parent / ".fnlifting-write-test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink(missing_ok=True)
    if database.exists():
        connection = sqlite3.connect(database)
        try:
            connection.execute("PRAGMA integrity_check")
        finally:
            connection.close()


def backup_database_before_migration() -> Path | None:
    database = sqlite_database_path()
    if not database or not database.exists() or database.stat().st_size == 0:
        return None
    backup_dir = env_path("BACKUP_DIR", database.parent / "backups") / "pre-migration"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"{database.stem}-{stamp}.sqlite3"
    shutil.copy2(database, backup)
    logging.info("pre-migration database backup created at %s", backup)
    return backup


def alembic_config() -> Config:
    root = resource_root()
    script_location = root / "alembic"
    if not script_location.exists():
        script_location = Path(__file__).resolve().parent / "alembic"
    config = Config()
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("prepend_sys_path", str(root))
    from app.core.config import settings

    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


def migrate() -> None:
    prepare_runtime_dirs()
    configure_logging()
    logging.info("migration start")
    ensure_sqlite_access()
    backup_database_before_migration()
    command.upgrade(alembic_config(), "head")
    logging.info("migration completed")


def seed() -> None:
    prepare_runtime_dirs()
    configure_logging()
    logging.info("seed start")
    from seed import seed_database

    seed_database(reset=False)
    logging.info("seed completed")


def serve() -> None:
    prepare_runtime_dirs()
    configure_logging()
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    logging.info("serve start on %s:%s", host, port)
    import uvicorn
    from app.main import app

    uvicorn.run(app, host=host, port=port, log_level=os.getenv("LOG_LEVEL", "info"))


def run() -> None:
    migrate()
    seed()
    serve()


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} backend standalone runtime")
    parser.add_argument("command", choices=["migrate", "seed", "serve", "run"])
    args = parser.parse_args()
    try:
        {"migrate": migrate, "seed": seed, "serve": serve, "run": run}[args.command]()
        return 0
    except Exception:
        configure_logging()
        logging.exception("backend standalone command failed: %s", args.command)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
