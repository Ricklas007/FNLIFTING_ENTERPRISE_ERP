import base64
import hashlib
import io
import json
import os
import secrets
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import DATA_DIR, settings
from app.database.session import engine
from app.models import BackupRecord


BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
MAGIC = b"FNLIFTING-BACKUP-V1\n"
INCLUDED_DIRS = ("certificates", "documents", "financial", "signatures")


def _key(password: str, salt: bytes) -> bytes:
    derived = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000).derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(derived)


def _database_path() -> Path:
    if not settings.database_url.startswith("sqlite") or not engine.url.database:
        raise ValueError("Backup integrado disponível apenas para a base SQLite local")
    return Path(engine.url.database).resolve()


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_database(destination: Path) -> None:
    source = sqlite3.connect(_database_path())
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def create_backup(db: Session, company_id: str, user_id: str, password: str, include_files: bool, notes: str | None) -> BackupRecord:
    sequence = (db.scalar(select(func.count(BackupRecord.id)).where(BackupRecord.company_id == company_id)) or 0) + 1
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_no = f"FNL-BKP-{datetime.now().year}-{sequence:04d}"
    file_name = f"{backup_no}-{timestamp}.fnlbak"
    output_path = (BACKUP_DIR / file_name).resolve()

    with tempfile.TemporaryDirectory(prefix="fnl-backup-") as temporary:
        temp_dir = Path(temporary)
        database_snapshot = temp_dir / "database.sqlite3"
        archive_path = temp_dir / "payload.zip"
        _snapshot_database(database_snapshot)
        manifest = {
            "format": "FNLBAK-1",
            "backup_no": backup_no,
            "app_version": settings.app_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_sha256": _checksum(database_snapshot),
            "includes_files": include_files,
            "files": [],
        }
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.write(database_snapshot, "database.sqlite3")
            if include_files:
                for directory_name in INCLUDED_DIRS:
                    directory = DATA_DIR / directory_name
                    if not directory.exists():
                        continue
                    for source in directory.rglob("*"):
                        if not source.is_file():
                            continue
                        relative = source.relative_to(DATA_DIR).as_posix()
                        archive.write(source, f"files/{relative}")
                        manifest["files"].append({"path": relative, "sha256": _checksum(source), "size": source.stat().st_size})
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        salt = secrets.token_bytes(16)
        token = Fernet(_key(password, salt)).encrypt(archive_path.read_bytes())
        output_path.write_bytes(MAGIC + salt + token)

    return BackupRecord(
        company_id=company_id,
        backup_no=backup_no,
        file_name=file_name,
        file_path=str(output_path),
        file_size=output_path.stat().st_size,
        checksum_sha256=_checksum(output_path),
        format_version="FNLBAK-1",
        encrypted=True,
        includes_files=include_files,
        status="ready",
        triggered_by="manual",
        notes=notes,
        created_by=user_id,
    )


def create_configured_backup(db: Session, company_id: str, user_id: str, include_files: bool, notes: str | None) -> BackupRecord:
    if len(settings.backup_encryption_key) < 32:
        raise ValueError("BACKUP_ENCRYPTION_KEY deve estar configurada com pelo menos 32 caracteres")
    return create_backup(db, company_id, user_id, settings.backup_encryption_key, include_files, notes)


def backup_path(record: BackupRecord) -> Path:
    path = Path(record.file_path).resolve()
    if BACKUP_DIR.resolve() not in path.parents or not path.is_file():
        raise ValueError("Ficheiro de backup indisponível")
    if _checksum(path) != record.checksum_sha256:
        raise ValueError("A integridade do backup não pôde ser confirmada")
    return path


def _decrypt(record: BackupRecord, password: str) -> bytes:
    raw = backup_path(record).read_bytes()
    if not raw.startswith(MAGIC) or len(raw) <= len(MAGIC) + 16:
        raise ValueError("Formato de backup inválido")
    salt = raw[len(MAGIC):len(MAGIC) + 16]
    try:
        return Fernet(_key(password, salt)).decrypt(raw[len(MAGIC) + 16:])
    except InvalidToken as exc:
        raise ValueError("Palavra-passe incorreta ou backup corrompido") from exc


def inspect_backup(record: BackupRecord, password: str) -> dict:
    payload = _decrypt(record, password)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        if "database.sqlite3" not in names or "manifest.json" not in names:
            raise ValueError("Conteúdo obrigatório em falta no backup")
        manifest = json.loads(archive.read("manifest.json"))
        database_bytes = archive.read("database.sqlite3")
        if hashlib.sha256(database_bytes).hexdigest() != manifest.get("database_sha256"):
            raise ValueError("Snapshot da base de dados corrompido")
        for name in names:
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("Caminho inseguro encontrado no backup")
    return manifest


def restore_backup(record: BackupRecord, password: str) -> dict:
    payload = _decrypt(record, password)
    with tempfile.TemporaryDirectory(prefix="fnl-restore-") as temporary:
        temp_dir = Path(temporary)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            database_bytes = archive.read("database.sqlite3")
            if hashlib.sha256(database_bytes).hexdigest() != manifest.get("database_sha256"):
                raise ValueError("Snapshot da base de dados corrompido")
            snapshot = temp_dir / "database.sqlite3"
            snapshot.write_bytes(database_bytes)

            engine.dispose()
            source = sqlite3.connect(snapshot)
            target = sqlite3.connect(_database_path())
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            engine.dispose()

            restored_files = 0
            for item in manifest.get("files", []):
                relative = Path(item["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Caminho inseguro encontrado no backup")
                member = f"files/{relative.as_posix()}"
                content = archive.read(member)
                if hashlib.sha256(content).hexdigest() != item.get("sha256"):
                    raise ValueError(f"Ficheiro corrompido: {relative.as_posix()}")
                destination = (DATA_DIR / relative).resolve()
                if DATA_DIR.resolve() not in destination.parents:
                    raise ValueError("Destino de restauro fora da pasta de dados")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
                restored_files += 1

    return {"backup_no": record.backup_no, "restored_files": restored_files, "manifest": manifest}
