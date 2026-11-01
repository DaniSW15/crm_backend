from abc import ABC, abstractmethod
from uuid import UUID

from src.modules.crm.domain.entities.customer import Customer


class CustomerRepository(ABC):
    @abstractmethod
    async def list(self, tenant_id: UUID, limit: int = 50, offset: int = 0) -> list[Customer]:
        pass

    @abstractmethod
    async def get_by_id(self, customer_id: UUID, tenant_id: UUID) -> Customer | None:
        pass

    @abstractmethod
    async def owner_exists(self, owner_id: UUID, tenant_id: UUID) -> bool:
        pass

    @abstractmethod
    async def save(self, customer: Customer) -> Customer:
        pass
