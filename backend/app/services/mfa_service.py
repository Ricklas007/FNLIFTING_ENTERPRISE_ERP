import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import MFARecoveryCode, User, UserMFAFactor
from app.security.mfa import generate_totp_secret, provisioning_uri, qr_png_data_uri, verify_totp
from app.services.enterprise_utils import now_utc


def has_active_mfa(db: Session, user_id: str) -> bool:
    return bool(db.scalar(select(UserMFAFactor.id).where(
        UserMFAFactor.user_id == user_id,
        UserMFAFactor.status == "active",
        UserMFAFactor.confirmed_at.is_not(None),
        UserMFAFactor.deleted_at.is_(None),
    )))


def start_setup(db: Session, user: User) -> dict:
    if has_active_mfa(db, user.id):
        raise ValueError("MFA já está ativo para este utilizador")
    pending = db.scalar(select(UserMFAFactor).where(
        UserMFAFactor.user_id == user.id,
        UserMFAFactor.status == "pending",
        UserMFAFactor.deleted_at.is_(None),
    ))
    secret = generate_totp_secret()
    if not pending:
        pending = UserMFAFactor(user_id=user.id, secret=secret, created_by=user.id)
        db.add(pending)
    pending.secret = secret
    pending.label = "Aplicação autenticadora"
    pending.status = "pending"
    pending.confirmed_at = None
    uri = provisioning_uri(secret, user.email)
    return {"secret": secret, "otpauth_uri": uri, "qr_code_data_uri": qr_png_data_uri(uri), "digits": 6, "period": 30}


def confirm_setup(db: Session, user: User, code: str) -> list[str] | None:
    factor = db.scalar(select(UserMFAFactor).where(
        UserMFAFactor.user_id == user.id,
        UserMFAFactor.status == "pending",
        UserMFAFactor.deleted_at.is_(None),
    ))
    if not factor or not verify_totp(factor.secret, code):
        return None
    factor.status = "active"
    factor.confirmed_at = now_utc()
    recovery_codes: list[str] = []
    for item in db.scalars(select(MFARecoveryCode).where(MFARecoveryCode.user_id == user.id, MFARecoveryCode.used_at.is_(None))):
        item.status = "revoked"
        item.used_at = now_utc()
    for _ in range(8):
        recovery = f"FNL-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
        recovery_codes.append(recovery)
        db.add(MFARecoveryCode(user_id=user.id, code_hash=hash_password(recovery), status="active", created_by=user.id))
    return recovery_codes


def disable_mfa(db: Session, user: User) -> None:
    for factor in db.scalars(select(UserMFAFactor).where(UserMFAFactor.user_id == user.id, UserMFAFactor.deleted_at.is_(None))):
        factor.status = "disabled"
        factor.updated_by = user.id
    for code in db.scalars(select(MFARecoveryCode).where(MFARecoveryCode.user_id == user.id, MFARecoveryCode.used_at.is_(None))):
        code.status = "revoked"
        code.used_at = now_utc()
