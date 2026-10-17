import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Clase base de SQLAlchemy 2.0 para todos los modelos del sistema."""
    pass


class UUIDPrimaryKeyMixin:
    """Clase mixin para clave primaria UUID."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-10,
    )


class TimestampMixin:
    """Clase mixin para marcas de tiempo automáticas con zona horaria."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        sort_order=101,
    )


class SoftDeleteMixin:
    """Mixin para borrado lógico (Soft delete)."""
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        sort_order=102,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        sort_order=103,
    )


class TenantMixin:
    """
    Mixin obligatorio para entidades que pertenecen a una Organización (Tenant).
    Fundamental para PostgreSQL Row Level Security (RLS).
    """
    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("identity_tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            sort_order=-5,
        )

