import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import InvalidTokenError, create_token, decode_token, hash_password, verify_password
from app.database.session import get_db
from app.models import Company, LoginHistory, MFAChallenge, MFARecoveryCode, Role, User, UserMFAFactor, UserSession
from app.schemas.auth import (
    LoginRequest,
    MFARequiredResponse,
    MFALoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.security.mfa import verify_totp


router = APIRouter(prefix="/auth", tags=["Autenticação"])


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        account_type=user.account_type,
        status=user.status,
        company=user.company,
        roles=user.roles,
        permissions=sorted(user.permission_codes),
        last_login_at=user.last_login_at,
    )


def load_user(db: Session, user_id: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.company), selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )


def issue_tokens(db: Session, user: User, request: Request, remember: bool) -> TokenResponse:
    previous_skip_sync = db.info.get("skip_sync_queue", False)
    db.info["skip_sync_queue"] = True
    try:
        refresh_days = 30 if remember else settings.refresh_token_days
        access_minutes = 8 * 60 if remember else settings.access_token_minutes
        refresh_jti = secrets.token_urlsafe(24)
        session = UserSession(
            user_id=user.id,
            refresh_jti=refresh_jti,
            user_agent=request.headers.get("user-agent", "")[:500],
            ip_address=request.client.host if request.client else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=refresh_days),
        )
        db.add(session)
        db.flush()
        access = create_token(user.id, session.id, user.company_id, "access", timedelta(minutes=access_minutes))
        refresh = create_token(
            user.id,
            session.id,
            user.company_id,
            "refresh",
            timedelta(days=refresh_days),
            {"refresh_jti": refresh_jti},
        )
        db.commit()
        hydrated = load_user(db, user.id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=access_minutes * 60,
            user=user_out(hydrated),
        )
    finally:
        db.info["skip_sync_queue"] = previous_skip_sync


@router.post("/login", response_model=TokenResponse | MFARequiredResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip().lower()
    recent_failures = db.scalar(select(LoginHistory).where(
        LoginHistory.identifier == identifier,
        LoginHistory.success.is_(False),
        LoginHistory.created_at >= datetime.now(timezone.utc) - timedelta(minutes=15),
    ).limit(1).offset(4))
    if recent_failures:
        raise HTTPException(status_code=429, detail="Conta temporariamente bloqueada por tentativas falhadas. Tente novamente mais tarde.")
    user = db.scalar(
        select(User)
        .options(selectinload(User.company), selectinload(User.roles).selectinload(Role.permissions))
        .where(or_(User.email == identifier, User.username == identifier), User.deleted_at.is_(None))
    )
    portal_mismatch = user and (
        (payload.portal == "client" and user.account_type != "external")
        or (payload.portal == "staff" and user.account_type == "external")
    )
    valid = user and verify_password(payload.password, user.password_hash) and not portal_mismatch
    history = LoginHistory(
        user_id=user.id if user else None,
        identifier=identifier,
        success=bool(valid and user.status == "active"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    if not valid:
        history.reason = "Credenciais inválidas ou portal incorreto"
        db.add(history)
        db.commit()
        raise HTTPException(status_code=401, detail="Email/utilizador ou palavra-passe inválidos")
    if user.status != "active":
        history.reason = f"Conta {user.status}"
        db.add(history)
        db.commit()
        detail = "A sua conta aguarda aprovação" if user.status == "pending" else "A sua conta está bloqueada"
        raise HTTPException(status_code=403, detail=detail)
    db.add(history)
    db.flush()
    mfa_factor = db.scalar(select(UserMFAFactor).where(
        UserMFAFactor.user_id == user.id,
        UserMFAFactor.status == "active",
        UserMFAFactor.confirmed_at.is_not(None),
        UserMFAFactor.deleted_at.is_(None),
    ))
    if mfa_factor:
        challenge_token = secrets.token_urlsafe(36)
        challenge = MFAChallenge(
            user_id=user.id,
            challenge_token=challenge_token,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500],
            created_by=user.id,
        )
        history.reason = "MFA obrigatório"
        db.add(challenge)
        db.commit()
        return MFARequiredResponse(challenge_id=challenge_token, user_hint=user.email)
    user.last_login_at = datetime.now(timezone.utc)
    return issue_tokens(db, user, request, payload.remember_me)


@router.post("/login/mfa", response_model=TokenResponse)
def login_mfa(payload: MFALoginRequest, request: Request, db: Session = Depends(get_db)):
    challenge = db.scalar(select(MFAChallenge).where(
        MFAChallenge.challenge_token == payload.challenge_id,
        MFAChallenge.consumed_at.is_(None),
        MFAChallenge.deleted_at.is_(None),
    ))
    if not challenge or challenge.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Desafio MFA expirado ou inválido")
    user = load_user(db, challenge.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="Utilizador indisponível")
    factor = db.scalar(select(UserMFAFactor).where(
        UserMFAFactor.user_id == user.id,
        UserMFAFactor.status == "active",
        UserMFAFactor.confirmed_at.is_not(None),
        UserMFAFactor.deleted_at.is_(None),
    ))
    valid = bool(factor and verify_totp(factor.secret, payload.code))
    recovery_used = None
    if not valid:
        for recovery_code in db.scalars(select(MFARecoveryCode).where(
            MFARecoveryCode.user_id == user.id,
            MFARecoveryCode.status == "active",
            MFARecoveryCode.used_at.is_(None),
        )):
            if verify_password(payload.code.strip(), recovery_code.code_hash):
                valid = True
                recovery_used = recovery_code
                break
    if not valid:
        db.add(LoginHistory(
            user_id=user.id,
            identifier=user.email,
            success=False,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500],
            reason="Código MFA inválido",
        ))
        db.commit()
        raise HTTPException(status_code=401, detail="Código MFA inválido")
    challenge.consumed_at = datetime.now(timezone.utc)
    user.last_login_at = datetime.now(timezone.utc)
    if factor:
        factor.last_used_at = datetime.now(timezone.utc)
    if recovery_used:
        recovery_used.used_at = datetime.now(timezone.utc)
        recovery_used.status = "used"
    db.add(LoginHistory(
        user_id=user.id,
        identifier=user.email,
        success=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
        reason="MFA validado",
    ))
    db.flush()
    return issue_tokens(db, user, request, payload.remember_me)


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email, username = payload.email.lower(), payload.username.lower()
    exists = db.scalar(select(User.id).where(or_(User.email == email, User.username == username)))
    if exists:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este email ou utilizador")
    if payload.account_type == "external":
        if not payload.company_name:
            raise HTTPException(status_code=422, detail="O nome da empresa é obrigatório para clientes")
        company = db.scalar(select(Company).where(Company.nif == payload.company_nif)) if payload.company_nif else None
        if not company:
            company = Company(
                name=payload.company_name,
                legal_name=payload.company_name,
                nif=payload.company_nif,
                company_type="client",
                status="pending",
            )
            db.add(company)
            db.flush()
    else:
        company = db.scalar(select(Company).where(Company.company_type == "owner"))
    user = User(
        company_id=company.id,
        email=email,
        username=username,
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        requested_role="client_external" if payload.account_type == "external" else payload.requested_role,
        account_type=payload.account_type,
        status="pending",
    )
    db.add(user)
    db.commit()
    return MessageResponse(message="Pedido recebido. A conta ficará disponível após aprovação do Administrador ou RH.")


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise ValueError
    except (InvalidTokenError, ValueError):
        raise HTTPException(status_code=401, detail="Token de renovação inválido")
    session = db.scalar(select(UserSession).where(UserSession.id == claims.get("sid")))
    if not session or session.revoked_at or session.refresh_jti != claims.get("refresh_jti"):
        raise HTTPException(status_code=401, detail="Sessão terminada")
    session.revoked_at = datetime.now(timezone.utc)
    db.flush()
    user = load_user(db, claims["sub"])
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="Utilizador indisponível")
    return issue_tokens(db, user, request, False)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    claims = decode_token(token)
    session = db.scalar(select(UserSession).where(UserSession.id == claims["sid"]))
    if session:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return MessageResponse(message="Sessão terminada com segurança")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password():
    return MessageResponse(
        message="Se a conta existir, o pedido foi registado. No modo local, contacte o Administrador para redefinir a palavra-passe."
    )
