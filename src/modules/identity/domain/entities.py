from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.shared.domain.exceptions import BusinessRuleViolationException


@dataclass
class Tenant:
    id: UUID
    name: str
    slug: str
    plan: str = "STARTER"
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class User:
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    hashed_password: str
    role: str = "CLIENTE"  # ADMIN (Jefe), DEV (Desarrollo), CLIENTE (Usuario)
    is_active: bool = True

    def change_role(self, new_role: str) -> None:
        valid_roles = {"ADMIN", "DEV", "CLIENTE", "SALES_MANAGER", "SALES_REP"}
        if new_role not in valid_roles:
            raise BusinessRuleViolationException(f"Rol '{new_role}' no es válido.")
        self.role = new_role

