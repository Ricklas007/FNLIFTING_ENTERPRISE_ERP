from datetime import datetime

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoleOut(BaseModel):
    name: str
    display_name: str
    model_config = ConfigDict(from_attributes=True)


class CompanyOut(BaseModel):
    id: str
    name: str
    company_type: str
    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    account_type: str
    status: str
    company: CompanyOut
    roles: list[RoleOut]
    permissions: list[str]
    last_login_at: datetime | None = None


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=180)
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = False
    portal: str = Field(default="staff", pattern="^(staff|client)$")


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=180)
    email: str
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    phone: str | None = Field(default=None, max_length=40)
    password: str = Field(min_length=10, max_length=128)
    requested_role: str = Field(min_length=2, max_length=80)
    account_type: str = Field(default="internal", pattern="^(internal|external)$")
    company_name: str | None = Field(default=None, max_length=180)
    company_nif: str | None = Field(default=None, max_length=40)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(c.isupper() for c in value) or not any(c.islower() for c in value):
            raise ValueError("A palavra-passe deve conter letras maiúsculas e minúsculas")
        if not any(c.isdigit() for c in value):
            raise ValueError("A palavra-passe deve conter pelo menos um número")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Introduza um endereço de email válido")
        return normalized


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MFARequiredResponse(BaseModel):
    mfa_required: bool = True
    challenge_id: str
    expires_in: int = 300
    user_hint: str
    delivery: str = "totp"


class MFALoginRequest(BaseModel):
    challenge_id: str = Field(min_length=20, max_length=160)
    code: str = Field(min_length=6, max_length=40)
    remember_me: bool = False


class MessageResponse(BaseModel):
    message: str
