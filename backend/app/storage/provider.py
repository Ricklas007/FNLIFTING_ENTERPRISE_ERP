from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import ATTACHMENT_DIR, settings


class StorageError(RuntimeError):
    """Erro controlado da camada de armazenamento."""


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    checksum_sha256: str
    mime_type: str
    provider: str
    url: str | None = None


@dataclass(frozen=True)
class StorageHealth:
    provider: str
    status: str
    configured: bool
    bucket: str
    message: str


class StorageProvider(Protocol):
    provider: str

    def health(self) -> StorageHealth:
        ...

    def put_bytes(self, key: str, payload: bytes, mime_type: str | None = None) -> StoredObject:
        ...

    def get_bytes(self, key: str) -> bytes:
        ...

    def delete(self, key: str) -> None:
        ...

    def presigned_get_url(self, key: str, expires_seconds: int = 900) -> str | None:
        ...


def _safe_key(key: str) -> str:
    normalized = key.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in {"..", "."} for part in parts):
        raise StorageError("Chave de armazenamento inválida")
    return "/".join(parts)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class LocalStorageProvider:
    provider = "LOCAL"

    def __init__(self, root: Path | None = None):
        self.root = (root or ATTACHMENT_DIR).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = _safe_key(key)
        target = (self.root / safe).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise StorageError("Chave de armazenamento fora da raiz permitida") from exc
        return target

    def health(self) -> StorageHealth:
        probe = self.root / ".storage-health"
        try:
            probe.write_bytes(b"ok")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            return StorageHealth(self.provider, "FAILED", True, str(self.root), f"Sem escrita no storage local: {exc.__class__.__name__}")
        return StorageHealth(self.provider, "CONNECTED", True, str(self.root), "Storage local pronto.")

    def put_bytes(self, key: str, payload: bytes, mime_type: str | None = None) -> StoredObject:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        detected_mime = mime_type or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        return StoredObject(
            key=_safe_key(key),
            size_bytes=len(payload),
            checksum_sha256=_sha256(payload),
            mime_type=detected_mime,
            provider=self.provider,
            url=None,
        )

    def get_bytes(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise StorageError("Objeto não encontrado no storage local")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def presigned_get_url(self, key: str, expires_seconds: int = 900) -> str | None:
        _safe_key(key)
        return None


class S3CompatibleStorageProvider:
    provider = "S3"

    def __init__(self):
        self.bucket = settings.storage_bucket
        self.endpoint_url = settings.storage_endpoint_url or None
        self.region = settings.storage_region
        self._client = None

    def _boto3(self):
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise StorageError("boto3 não instalado; instale requirements para usar S3/MinIO") from exc
        return boto3

    def _s3_client(self):
        if self._client is None:
            boto3 = self._boto3()
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region,
                aws_access_key_id=settings.storage_access_key_id or None,
                aws_secret_access_key=settings.storage_secret_access_key or None,
                use_ssl=settings.storage_secure,
            )
        return self._client

    def health(self) -> StorageHealth:
        configured = bool(self.bucket and (settings.storage_access_key_id or not self.endpoint_url))
        if not configured:
            return StorageHealth(self.provider, "NOT_CONFIGURED", False, self.bucket, "Storage S3/MinIO sem bucket ou credenciais.")
        try:
            self._s3_client().head_bucket(Bucket=self.bucket)
        except StorageError as exc:
            return StorageHealth(self.provider, "DRIVER_MISSING", configured, self.bucket, str(exc))
        except Exception as exc:  # pragma: no cover - depende de provider externo
            return StorageHealth(self.provider, "DEGRADED", configured, self.bucket, f"Provider respondeu {exc.__class__.__name__}.")
        return StorageHealth(self.provider, "CONNECTED", configured, self.bucket, "Storage S3/MinIO conectado.")

    def put_bytes(self, key: str, payload: bytes, mime_type: str | None = None) -> StoredObject:
        safe = _safe_key(key)
        detected_mime = mime_type or mimetypes.guess_type(safe)[0] or "application/octet-stream"
        self._s3_client().put_object(Bucket=self.bucket, Key=safe, Body=payload, ContentType=detected_mime, Metadata={"sha256": _sha256(payload)})
        return StoredObject(safe, len(payload), _sha256(payload), detected_mime, self.provider, self.presigned_get_url(safe))

    def get_bytes(self, key: str) -> bytes:
        safe = _safe_key(key)
        response = self._s3_client().get_object(Bucket=self.bucket, Key=safe)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self._s3_client().delete_object(Bucket=self.bucket, Key=_safe_key(key))

    def presigned_get_url(self, key: str, expires_seconds: int = 900) -> str | None:
        safe = _safe_key(key)
        return self._s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": safe},
            ExpiresIn=expires_seconds,
        )


def get_storage_provider() -> StorageProvider:
    provider = settings.storage_provider.upper()
    if provider in {"LOCAL", ""}:
        return LocalStorageProvider()
    if provider in {"S3", "MINIO"}:
        service = S3CompatibleStorageProvider()
        service.provider = provider
        return service
    raise StorageError(f"Storage provider não suportado: {settings.storage_provider}")
