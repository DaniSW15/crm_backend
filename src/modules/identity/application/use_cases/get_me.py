from dataclasses import dataclass
from uuid import UUID

from src.modules.identity.application.ports.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.domain.entities import Tenant, User
from src.shared.domain.exceptions import EntityNotFoundException


@dataclass
class UserProfileResult:
    user: User
    tenant: Tenant


class GetMeUseCase:
    """Caso de uso: Obtener el perfil completo del usuario autenticado y su organización."""

    def __init__(self, identity_repo: IdentityRepository):
        self.identity_repo = identity_repo

    async def execute(self, user_id: UUID) -> UserProfileResult:
        user = await self.identity_repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("El usuario autenticado ya no existe.")

        tenant = await self.identity_repo.get_tenant_by_id(user.tenant_id)
        if not tenant:
            raise EntityNotFoundException("La organización asociada ya no existe.")

        return UserProfileResult(user=user, tenant=tenant)

