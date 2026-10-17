from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.modules.identity.domain.entities import Tenant, User


class IdentityRepository(ABC):
    """
    Puerto (Interface) para persistencia de Tenants y Usuarios.
    """

    @abstractmethod
    async def get_tenant_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        pass

    @abstractmethod
    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        pass

    @abstractmethod
    async def save_tenant(self, tenant: Tenant) -> Tenant:
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str, tenant_id: Optional[UUID] = None) -> Optional[User]:
        pass

    @abstractmethod
    async def save_user(self, user: User) -> User:
        pass

