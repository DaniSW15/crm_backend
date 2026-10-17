import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.infrastructure.base_model import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class AccountModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """
    Empresa cliente (Cuenta B2B).
    """
    __tablename__ = "crm_accounts"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    annual_revenue: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relaciones
    contacts: Mapped[List["ContactModel"]] = relationship("ContactModel", back_populates="account")
    deals: Mapped[List["DealModel"]] = relationship("DealModel", back_populates="account")

    __table_args__ = (
        Index("idx_crm_accounts_tenant_name", "tenant_id", "name"),
        Index("idx_crm_accounts_custom_fields", "custom_fields", postgresql_using="gin"),
    )


class ContactModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """
    Persona individual o contacto en una empresa.
    """
    __tablename__ = "crm_contacts"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relaciones
    account: Mapped[Optional["AccountModel"]] = relationship("AccountModel", back_populates="contacts")
    deals: Mapped[List["DealModel"]] = relationship("DealModel", back_populates="primary_contact")

    __table_args__ = (
        Index("idx_crm_contacts_tenant_email", "tenant_id", "email"),
        Index("idx_crm_contacts_tenant_account", "tenant_id", "account_id"),
    )


class LeadModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """
    Prospecto antes de ser calificado.
    """
    __tablename__ = "crm_leads"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="WEBSITE", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)  # NEW, CONTACTED, QUALIFIED, UNQUALIFIED, CONVERTED

    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Si se convierte, guarda las referencias creadas
    converted_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    converted_contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    converted_deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    custom_fields: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        Index("idx_crm_leads_tenant_status", "tenant_id", "status"),
    )


class PipelineModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """
    Embudo de Ventas (proceso comercial).
    """
    __tablename__ = "crm_pipelines"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    stages: Mapped[List["PipelineStageModel"]] = relationship(
        "PipelineStageModel",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="PipelineStageModel.order",
    )
    deals: Mapped[List["DealModel"]] = relationship("DealModel", back_populates="pipeline")

    __table_args__ = (
        Index("idx_crm_pipelines_tenant_active", "tenant_id", "is_active"),
    )


class PipelineStageModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """
    Etapa dentro de un embudo comercial (ej. Prospección, Demostración, Ganada).
    """
    __tablename__ = "crm_pipeline_stages"

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(default=0, nullable=False)
    win_probability: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)  # 0.0 a 100.0%
    days_until_stale: Mapped[int] = mapped_column(default=14, nullable=False)
    is_won_stage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_lost_stage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relaciones
    pipeline: Mapped["PipelineModel"] = relationship("PipelineModel", back_populates="stages")
    deals: Mapped[List["DealModel"]] = relationship("DealModel", back_populates="stage")

    __table_args__ = (
        Index("idx_crm_stages_pipeline_order", "tenant_id", "pipeline_id", "order"),
    )


class DealModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """
    Oportunidad comercial / Trato económico en negociación.
    """
    __tablename__ = "crm_deals"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)  # OPEN, WON, LOST

    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_pipelines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_pipeline_stages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    expected_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_close_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relaciones
    account: Mapped[Optional["AccountModel"]] = relationship("AccountModel", back_populates="deals")
    primary_contact: Mapped[Optional["ContactModel"]] = relationship("ContactModel", back_populates="deals")
    pipeline: Mapped["PipelineModel"] = relationship("PipelineModel", back_populates="deals")
    stage: Mapped["PipelineStageModel"] = relationship("PipelineStageModel", back_populates="deals")
    stage_history: Mapped[List["DealStageHistoryModel"]] = relationship(
        "DealStageHistoryModel",
        back_populates="deal",
        cascade="all, delete-orphan",
    )
    activities: Mapped[List["ActivityModel"]] = relationship(
        "ActivityModel",
        back_populates="deal",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_crm_deals_tenant_stage", "tenant_id", "stage_id"),
        Index("idx_crm_deals_tenant_status", "tenant_id", "status"),
        Index("idx_crm_deals_tenant_owner", "tenant_id", "owner_id"),
    )


class DealStageHistoryModel(Base, UUIDPrimaryKeyMixin, TenantMixin):
    """
    Registro histórico inmutable de transiciones de etapas para analítica y embudo de conversión.
    """
    __tablename__ = "crm_deal_stage_history"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_stage_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_pipeline_stages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relación
    deal: Mapped["DealModel"] = relationship("DealModel", back_populates="stage_history")

    __table_args__ = (
        Index("idx_crm_stage_history_deal_transition", "tenant_id", "deal_id", "transitioned_at"),
    )


class ActivityModel(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """
    Interacción con clientes (Llamadas, Reuniones, Notas, Tareas pendientes).
    """
    __tablename__ = "crm_activities"

    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CALL, MEETING, NOTE, TASK, EMAIL
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_deals.id", ondelete="CASCADE"),
        nullable=True,
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_contacts.id", ondelete="CASCADE"),
        nullable=True,
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_accounts.id", ondelete="CASCADE"),
        nullable=True,
    )
    assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relaciones
    deal: Mapped[Optional["DealModel"]] = relationship("DealModel", back_populates="activities")

    __table_args__ = (
        Index("idx_crm_activities_tenant_assigned", "tenant_id", "assigned_user_id", "is_completed"),
        Index("idx_crm_activities_tenant_deal", "tenant_id", "deal_id"),
    )

