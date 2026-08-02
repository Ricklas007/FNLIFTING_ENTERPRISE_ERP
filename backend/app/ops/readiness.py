from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import (
    ATTACHMENT_DIR,
    BACKUP_DIR,
    CERTIFICATE_DIR,
    DATA_DIR,
    EXPORT_DIR,
    INVOICE_DIR,
    LOG_DIR,
    MAP_CACHE_DIR,
    MAP_DIR,
    RECEIPT_DIR,
    REPORT_DIR,
    TEMP_DIR,
    UPLOAD_DIR,
    settings,
)
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import BackupRecord, Company, SyncQueue, User
from app.storage import StorageError, get_storage_provider


CheckStatus = str

DEFAULT_SECRET_MARKERS = ("change-this-key", "replace-with", "test-secret")


def _check(key: str, label: str, status: CheckStatus, message: str, recommendation: str | None = None) -> dict:
    return {
        "key": key,
        "label": label,
        "status": status,
        "message": message,
        "recommendation": recommendation,
    }


def _masked_database_url(url: str) -> str:
    if url.startswith("sqlite"):
        return url
    parsed = urlsplit(url)
    if not parsed.password:
        return url
    username = parsed.username or ""
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{username}:***@{hostname}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _secret_check() -> dict:
    secret = settings.secret_key or ""
    default_secret = any(marker in secret.lower() for marker in DEFAULT_SECRET_MARKERS)
    if len(secret) < 32 or default_secret:
        status = "fail" if settings.is_production else "warn"
        return _check(
            "secret_key",
            "Chave JWT",
            status,
            "A SECRET_KEY ainda é fraca ou parece ser de demonstração.",
            "Defina SECRET_KEY com pelo menos 32 caracteres aleatórios antes de usar dados reais.",
        )
    return _check("secret_key", "Chave JWT", "pass", "SECRET_KEY configurada com tamanho adequado.")


def _runtime_check() -> list[dict]:
    checks = []
    if settings.is_production and settings.debug:
        checks.append(_check(
            "debug",
            "Modo debug",
            "fail",
            "DEBUG=true em ambiente de produção.",
            "Defina DEBUG=false no ficheiro .env de produção.",
        ))
    else:
        checks.append(_check("debug", "Modo debug", "pass", f"Debug {'ativo' if settings.debug else 'desativado'} em {settings.environment}."))

    origins = settings.cors_origin_list
    if settings.is_production and "*" in origins:
        checks.append(_check(
            "cors",
            "CORS",
            "fail",
            "CORS permite qualquer origem em produção.",
            "Defina CORS_ORIGINS apenas com os domínios reais do ERP.",
        ))
    elif settings.is_production and any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
        checks.append(_check(
            "cors",
            "CORS",
            "warn",
            "CORS ainda contém origens locais.",
            "Troque localhost/127.0.0.1 pelo domínio HTTPS usado pela empresa.",
        ))
    else:
        checks.append(_check("cors", "CORS", "pass", f"{len(origins)} origem(ns) configurada(s)."))

    allowed_hosts = settings.allowed_host_list
    if settings.is_production and ("*" in allowed_hosts or not allowed_hosts):
        checks.append(_check(
            "allowed_hosts",
            "Hosts permitidos",
            "fail",
            "Hosts permitidos estão abertos ou vazios em produção.",
            "Defina ALLOWED_HOSTS com o domínio/IP real do backend.",
        ))
    else:
        checks.append(_check("allowed_hosts", "Hosts permitidos", "pass", f"{len(allowed_hosts)} host(s) configurado(s)."))
    return checks


def _database_checks() -> list[dict]:
    checks = []
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            inspector = inspect(connection)
            existing_tables = set(inspector.get_table_names())
    except SQLAlchemyError as exc:
        return [_check(
            "database",
            "Base de dados",
            "fail",
            f"Não foi possível ligar à base de dados: {exc.__class__.__name__}.",
            "Confirme DATABASE_URL, permissões do ficheiro SQLite ou credenciais PostgreSQL.",
        )]

    checks.append(_check("database", "Base de dados", "pass", f"Ligação ativa em {_masked_database_url(settings.database_url)}."))

    expected_tables = set(Base.metadata.tables)
    missing_tables = sorted(expected_tables - existing_tables)
    if missing_tables:
        checks.append(_check(
            "schema",
            "Schema",
            "fail",
            f"Faltam {len(missing_tables)} tabela(s): {', '.join(missing_tables[:6])}.",
            "Execute as migrações antes de arrancar em produção.",
        ))
    else:
        checks.append(_check("schema", "Schema", "pass", f"{len(expected_tables)} tabela(s) registada(s)."))

    if "alembic_version" in existing_tables:
        checks.append(_check("migrations", "Migrações", "pass", "Tabela alembic_version encontrada."))
    else:
        status = "fail" if settings.is_production and not settings.auto_create_schema else "warn"
        checks.append(_check(
            "migrations",
            "Migrações",
            status,
            "Base ainda não tem marcação de versão Alembic.",
            "Execute `alembic upgrade head` ou `scripts\\migrate.ps1` para marcar o baseline.",
        ))
    return checks


def _data_directory_checks() -> list[dict]:
    required = [
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
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        return [_check(
            "data_dirs",
            "Diretórios locais",
            "fail",
            f"Faltam diretórios de dados: {', '.join(path.name for path in missing)}.",
            "Crie os diretórios ou restaure a pasta backend/data a partir de backup.",
        )]
    try:
        with NamedTemporaryFile(prefix="fnl-readiness-", dir=DATA_DIR, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(b"ok")
        temp_path.unlink(missing_ok=True)
    except OSError as exc:
        return [_check(
            "data_dirs",
            "Diretórios locais",
            "fail",
            f"Sem permissão de escrita em {DATA_DIR}: {exc.__class__.__name__}.",
            "Ajuste permissões do utilizador que executa o backend.",
        )]
    return [_check("data_dirs", "Diretórios locais", "pass", "Pastas de dados existem e aceitam escrita.")]


def _storage_checks() -> list[dict]:
    try:
        health = get_storage_provider().health()
    except StorageError as exc:
        status = "fail" if settings.is_production else "warn"
        return [_check("object_storage", "Object storage", status, str(exc), "Configure STORAGE_PROVIDER=LOCAL, MINIO ou S3.")]
    if health.status == "CONNECTED":
        return [_check("object_storage", "Object storage", "pass", health.message)]
    status = "fail" if settings.is_production and settings.storage_provider.upper() in {"S3", "MINIO"} else "warn"
    return [_check("object_storage", "Object storage", status, health.message, "Valide bucket, endpoint e credenciais fora do Git.")]


def _business_checks() -> list[dict]:
    checks = []
    try:
        with SessionLocal() as db:
            company_count = db.scalar(select(func.count()).select_from(Company).where(Company.deleted_at.is_(None))) or 0
            user_count = db.scalar(select(func.count()).select_from(User).where(User.deleted_at.is_(None))) or 0
            latest_backup = db.scalar(
                select(BackupRecord)
                .where(BackupRecord.deleted_at.is_(None), BackupRecord.status == "ready")
                .order_by(BackupRecord.created_at.desc())
            )
            sync_statuses = Counter(
                db.scalars(select(SyncQueue.status).where(SyncQueue.deleted_at.is_(None))).all()
            )
    except SQLAlchemyError as exc:
        return [_check(
            "business_data",
            "Dados operacionais",
            "fail",
            f"Não foi possível consultar dados operacionais: {exc.__class__.__name__}.",
        )]

    if not company_count or not user_count:
        checks.append(_check(
            "seed_data",
            "Dados mínimos",
            "warn",
            "Não há empresas ou utilizadores ativos suficientes.",
            "Execute seed controlado ou crie a empresa e o primeiro administrador.",
        ))
    else:
        checks.append(_check("seed_data", "Dados mínimos", "pass", f"{company_count} empresa(s) e {user_count} utilizador(es) registado(s)."))

    backup_created_at = _as_aware(latest_backup.created_at if latest_backup else None)
    if not backup_created_at:
        checks.append(_check(
            "backup_recent",
            "Backup recente",
            "warn",
            "Ainda não existe backup cifrado pronto.",
            "Crie um backup completo antes de operar com dados reais.",
        ))
    else:
        age_hours = (datetime.now(timezone.utc) - backup_created_at).total_seconds() / 3600
        if age_hours > settings.backup_warning_hours:
            checks.append(_check(
                "backup_recent",
                "Backup recente",
                "warn",
                f"O último backup pronto tem {age_hours:.1f} hora(s).",
                f"Crie backup pelo menos a cada {settings.backup_warning_hours} hora(s).",
            ))
        else:
            checks.append(_check("backup_recent", "Backup recente", "pass", f"Último backup pronto há {age_hours:.1f} hora(s)."))

    conflicts = sync_statuses.get("conflict", 0)
    failed = sync_statuses.get("failed", 0)
    pending = sync_statuses.get("pending", 0)
    if conflicts or failed:
        checks.append(_check(
            "sync_queue",
            "Fila de sincronização",
            "warn",
            f"{conflicts} conflito(s), {failed} falha(s) e {pending} pendente(s).",
            "Resolva conflitos/falhas antes de promover o ambiente para produção.",
        ))
    else:
        checks.append(_check("sync_queue", "Fila de sincronização", "pass", f"{pending} item(ns) pendente(s), sem conflitos ou falhas."))
    return checks


def build_readiness_report() -> dict:
    checks = [
        _secret_check(),
        *_runtime_check(),
        *_database_checks(),
        *_data_directory_checks(),
        *_storage_checks(),
        *_business_checks(),
    ]
    summary = Counter(check["status"] for check in checks)
    ready = summary.get("fail", 0) == 0
    return {
        "status": "ready" if ready else "not_ready",
        "environment": settings.environment,
        "version": settings.app_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": _masked_database_url(settings.database_url),
        "auto_create_schema": settings.auto_create_schema,
        "summary": {
            "pass": summary.get("pass", 0),
            "warn": summary.get("warn", 0),
            "fail": summary.get("fail", 0),
        },
        "checks": checks,
        "deployment": {
            "docker_ready": True,
            "migrations_ready": True,
            "frontend_runtime": os.getenv("VITE_API_URL", "/api/v1"),
        },
    }
