from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.shared.domain.exceptions import BusinessRuleViolationException


@dataclass
class Customer:
    """Cliente B2B; comparte identidad con la cuenta comercial existente."""

    id: UUID
    tenant_id: UUID
    name: str
    industry: str | None = None
    website: str | None = None
    phone: str | None = None
    annual_revenue: Decimal | None = None
    owner_id: UUID | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)

    def validate_for_write(self) -> None:
        """Valida comandos sin impedir la lectura de cuentas históricas."""
        self.name = self.name.strip()
        if not 2 <= len(self.name) <= 200:
            raise BusinessRuleViolationException("El nombre del cliente debe tener entre 2 y 200 caracteres.")
        if self.annual_revenue is not None and (
            not self.annual_revenue.is_finite() or self.annual_revenue < 0
        ):
            raise BusinessRuleViolationException("Los ingresos anuales deben ser un decimal no negativo.")

    def updated(self, changes: dict[str, Any]) -> "Customer":
        allowed = {"name", "industry", "website", "phone", "annual_revenue", "owner_id", "custom_fields"}
        if changes.keys() - allowed:
            raise BusinessRuleViolationException("Hay campos de cliente que no se pueden modificar.")
        if changes.get("name", self.name) is None or changes.get("custom_fields", self.custom_fields) is None:
            raise BusinessRuleViolationException("El nombre y los campos personalizados no pueden ser nulos.")
        customer = replace(self, **changes)
        customer.validate_for_write()
        return customer
