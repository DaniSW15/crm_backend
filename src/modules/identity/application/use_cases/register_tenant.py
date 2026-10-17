import re
import uuid
from dataclasses import dataclass
from uuid import UUID

from src.core.security import create_access_token, hash_password
from src.modules.identity.application.ports.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.domain.entities import Tenant, User
from src.shared.domain.exceptions import BusinessRuleViolationException


@dataclass
class RegisterTenantCommand:
    company_name: str
    slug: str
    admin_full_name: str
    admin_email: str
    admin_password: str


@dataclass
class AuthResult:
    access_token: str
    token_type: str
    user_id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: str


class RegisterTenantUseCase:
    """Caso de uso: Registrar una nueva organización junto a su usuario administrador inicial."""

    def __init__(self, identity_repo: IdentityRepository):
        self.identity_repo = identity_repo

    async def execute(self, cmd: RegisterTenantCommand) -> AuthResult:
        # Normalizar slug (solo letras, números y guiones)
        clean_slug = re.sub(r"[^a-zA-Z0-9-]", "", cmd.slug.lower().strip())
        if not clean_slug:
            raise BusinessRuleViolationException("El slug de la empresa no es válido.")

        # Verificar si el slug ya existe
        existing_tenant = await self.identity_repo.get_tenant_by_slug(clean_slug)
        if existing_tenant:
            raise BusinessRuleViolationException(f"La organización con slug '{clean_slug}' ya existe.")

        clean_email = cmd.admin_email.lower().strip()
        existing_user = await self.identity_repo.get_user_by_email(clean_email)
        if existing_user:
            raise BusinessRuleViolationException(f"El email '{clean_email}' ya está registrado.")

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Crear Tenant
        tenant = Tenant(
            id=tenant_id,
            name=cmd.company_name.strip(),
            slug=clean_slug,
            plan="PRO",
        )
        saved_tenant = await self.identity_repo.save_tenant(tenant)

        # Crear Administrador
        user = User(
            id=user_id,
            tenant_id=saved_tenant.id,
            email=clean_email,
            full_name=cmd.admin_full_name.strip(),
            hashed_password=hash_password(cmd.admin_password),
            role="ADMIN",
        )
        saved_user = await self.identity_repo.save_user(user)

        # Generar Token JWT con claims de multi-tenancy
        token = create_access_token(
            data={
                "sub": str(saved_user.id),
                "tenant_id": str(saved_tenant.id),
                "email": saved_user.email,
                "role": saved_user.role,
            }
        )

        return AuthResult(
            access_token=token,
            token_type="bearer",
            user_id=saved_user.id,
            tenant_id=saved_tenant.id,
            email=saved_user.email,
            full_name=saved_user.full_name,
            role=saved_user.role,
        )

