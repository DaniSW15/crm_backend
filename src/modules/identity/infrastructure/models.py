import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.infrastructure.base_model import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from src.modules.crm.infrastructure.models import DealModel


class TenantModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Representa una Organización o Inquilino (Tenant).
    Raíz del aislamiento de datos en la arquitectura multi-inquilino.
    """
    __tablename__ = "identity_tenants"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="STARTER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    users: Mapped[List["UserModel"]] = relationship(
        "UserModel",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class UserModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """
    Usuario del sistema perteneciente a un Tenant.
    """
    __tablename__ = "identity_users"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="SALES_REP", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    tenant: Mapped["TenantModel"] = relationship("TenantModel", back_populates="users")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tenant_user_email"),
        Index("idx_tenant_users_role", "tenant_id", "role"),
    )

