import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings


PBKDF2_ITERATIONS = 600_000


class InvalidTokenError(ValueError):
    pass


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            base64.urlsafe_b64decode(salt.encode()),
            int(iterations),
        )
        return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
    except (ValueError, TypeError):
        return False


def create_token(
    subject: str,
    session_id: str,
    company_id: str,
    token_type: str,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "sid": session_id,
        "company_id": company_id,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra:
        payload.update(extra)
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64_encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(settings.secret_key.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64_encode(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        expected = hmac.new(settings.secret_key.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64_decode(encoded_signature)):
            raise InvalidTokenError("Assinatura inválida")
        header = json.loads(_b64_decode(encoded_header))
        payload = json.loads(_b64_decode(encoded_payload))
        if header.get("alg") != "HS256" or payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
            raise InvalidTokenError("Token expirado ou algoritmo inválido")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
        if isinstance(exc, InvalidTokenError):
            raise
        raise InvalidTokenError("Token malformado") from exc
