from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.ports.customer_repository import CustomerRepository
from src.modules.crm.domain.entities.customer import Customer
from src.modules.crm.infrastructure.models import AccountModel
from src.modules.identity.infrastructure.models import UserModel


class SqlAlchemyCustomerRepository(CustomerRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_entity(model: AccountModel) -> Customer:
        return Customer(
            id=model.id, tenant_id=model.tenant_id, name=model.name,
            industry=model.industry, website=model.website, phone=model.phone,
            annual_revenue=model.annual_revenue, owner_id=model.owner_id,
            custom_fields=model.custom_fields or {},
        )

    async def list(self, tenant_id: UUID, limit: int = 50, offset: int = 0) -> list[Customer]:
        result = await self.session.execute(select(AccountModel).where(
            AccountModel.tenant_id == tenant_id, AccountModel.is_deleted.is_(False),
        ).order_by(AccountModel.created_at.desc(), AccountModel.id).limit(limit).offset(offset))
        return [self._to_entity(model) for model in result.scalars().all()]

    async def get_by_id(self, customer_id: UUID, tenant_id: UUID) -> Customer | None:
        result = await self.session.execute(select(AccountModel).where(
            AccountModel.id == customer_id, AccountModel.tenant_id == tenant_id,
            AccountModel.is_deleted.is_(False),
        ))
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def owner_exists(self, owner_id: UUID, tenant_id: UUID) -> bool:
        result = await self.session.execute(select(UserModel.id).where(
            UserModel.id == owner_id, UserModel.tenant_id == tenant_id,
            UserModel.is_deleted.is_(False),
        ))
        return result.scalar_one_or_none() is not None

    async def save(self, customer: Customer) -> Customer:
        result = await self.session.execute(select(AccountModel).where(
            AccountModel.id == customer.id, AccountModel.tenant_id == customer.tenant_id,
            AccountModel.is_deleted.is_(False),
        ))
        model = result.scalar_one_or_none()
        if model is None:
            model = AccountModel(id=customer.id, tenant_id=customer.tenant_id)
            self.session.add(model)
        for key in ("name", "industry", "website", "phone", "annual_revenue", "owner_id", "custom_fields"):
            setattr(model, key, getattr(customer, key))
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)
