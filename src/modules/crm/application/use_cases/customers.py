from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from src.modules.crm.application.ports.customer_repository import CustomerRepository
from src.modules.crm.domain.entities.customer import Customer
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.domain.exceptions import BusinessRuleViolationException, EntityNotFoundException


@dataclass
class CreateCustomerCommand:
    tenant_id: UUID
    name: str
    industry: str | None = None
    website: str | None = None
    phone: str | None = None
    annual_revenue: Decimal | None = None
    owner_id: UUID | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)


class CustomerUseCases:
    def __init__(self, repository: CustomerRepository, uow: UnitOfWork):
        self.repository = repository
        self.uow = uow

    async def list(self, tenant_id: UUID, limit: int = 50, offset: int = 0) -> list[Customer]:
        return await self.repository.list(tenant_id, limit, offset)

    async def get(self, customer_id: UUID, tenant_id: UUID) -> Customer:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if customer is None:
            raise EntityNotFoundException("El cliente no existe en esta organización.")
        return customer

    async def _validate_owner(self, customer: Customer) -> None:
        if customer.owner_id is not None and not await self.repository.owner_exists(
            customer.owner_id, customer.tenant_id
        ):
            raise BusinessRuleViolationException("El propietario no está disponible en esta organización.")

    async def create(self, command: CreateCustomerCommand) -> Customer:
        async with self.uow:
            customer = Customer(id=uuid4(), **vars(command))
            customer.validate_for_write()
            await self._validate_owner(customer)
            return await self.repository.save(customer)

    async def update(self, customer_id: UUID, tenant_id: UUID, changes: dict[str, Any]) -> Customer:
        async with self.uow:
            customer = (await self.get(customer_id, tenant_id)).updated(changes)
            await self._validate_owner(customer)
            return await self.repository.save(customer)
