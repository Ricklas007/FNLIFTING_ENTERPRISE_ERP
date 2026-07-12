from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Table, Text, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import RecordMixin


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Company(RecordMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(220))
    nif: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    company_type: Mapped[str] = mapped_column(String(30), default="client")
    status: Mapped[str] = mapped_column(String(20), default="active")

    users: Mapped[list["User"]] = relationship(back_populates="company")


class Permission(RecordMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    module: Mapped[str] = mapped_column(String(60), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    roles: Mapped[list["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")


class Role(RecordMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)

    permissions: Mapped[list[Permission]] = relationship(secondary=role_permissions, back_populates="roles")
    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")


class User(RecordMixin, Base):
    __tablename__ = "users"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180))
    password_hash: Mapped[str] = mapped_column(String(300))
    account_type: Mapped[str] = mapped_column(String(20), default="internal")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    requested_role: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(40))
    avatar_url: Mapped[str | None] = mapped_column(String(400))
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship(back_populates="users")
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def permission_codes(self) -> set[str]:
        if self.is_superuser:
            return {"*"}
        return {permission.code for role in self.roles for permission in role.permissions}


class UserSession(RecordMixin, Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_jti: Mapped[str] = mapped_column(String(100), unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class LoginHistory(RecordMixin, Base):
    __tablename__ = "login_history"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    identifier: Mapped[str] = mapped_column(String(180))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str | None] = mapped_column(String(200))

