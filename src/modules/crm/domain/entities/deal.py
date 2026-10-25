from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from src.shared.domain.exceptions import BusinessRuleViolationException


@dataclass
class Deal:
    """
    Entidad del Dominio: Oportunidad comercial (Deal/Opportunity).
    Contiene la lógica de negocio pura para cambios de etapa y cierre de ventas.
    """
    id: UUID
    tenant_id: UUID
    title: str
    amount: Decimal
    currency: str
    pipeline_id: UUID
    stage_id: UUID
    owner_id: UUID
    status: str = "OPEN"  # OPEN, WON, LOST
    account_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    expected_close_date: Optional[date] = None
    actual_close_date: Optional[datetime] = None
    lost_reason: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def change_stage(self, new_stage_id: UUID) -> None:
        """Mueve la oportunidad a una nueva etapa dentro del embudo."""
        if self.status != "OPEN":
            raise BusinessRuleViolationException(
                f"No se puede cambiar la etapa de un trato con estado '{self.status}'."
            )
        self.stage_id = new_stage_id

    def mark_as_won(self) -> None:
        """Cierra el trato exitosamente como ganado."""
        if self.status != "OPEN":
            raise BusinessRuleViolationException(
                f"El trato ya fue cerrado previamente como '{self.status}'."
            )
        self.status = "WON"
        self.actual_close_date = datetime.utcnow()

    def mark_as_lost(self, reason: str) -> None:
        """Cierra el trato como perdido indicando el motivo."""
        if not reason or not reason.strip():
            raise BusinessRuleViolationException(
                "Es obligatorio indicar el motivo de pérdida al marcar un trato como perdido."
            )
        if self.status != "OPEN":
            raise BusinessRuleViolationException(
                f"El trato ya fue cerrado previamente como '{self.status}'."
            )
        self.status = "LOST"
        self.lost_reason = reason.strip()
        self.actual_close_date = datetime.utcnow()

    def update_amount(self, amount: Decimal, currency: Optional[str] = None) -> None:
        """Actualiza el valor económico de la oportunidad."""
        if amount < Decimal("0.0"):
            raise BusinessRuleViolationException("El monto de una oportunidad no puede ser negativo.")
        self.amount = amount
        if currency:
            self.currency = currency.upper()

    def update_details(
        self,
        title: Optional[str] = None,
        amount: Optional[Decimal] = None,
        currency: Optional[str] = None,
        expected_close_date: Optional[date] = None,
        account_id: Optional[UUID] = None,
        contact_id: Optional[UUID] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Actualiza la información general de la oportunidad."""
        if title is not None:
            clean_title = title.strip()
            if len(clean_title) < 3:
                raise BusinessRuleViolationException("El título debe tener al menos 3 caracteres.")
            self.title = clean_title
        if amount is not None:
            self.update_amount(amount, currency)
        elif currency is not None:
            self.currency = currency.upper()
        if expected_close_date is not None:
            self.expected_close_date = expected_close_date
        if account_id is not None:
            self.account_id = account_id
        if contact_id is not None:
            self.contact_id = contact_id
        if custom_fields is not None:
            self.custom_fields = custom_fields

