from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.ports.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.domain.entities import Tenant, User
from src.modules.identity.infrastructure.models import TenantModel, UserModel


class SqlAlchemyIdentityRepository(IdentityRepository):
    """
    Implementación del repositorio de identidad usando SQLAlchemy 2.0.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_tenant_entity(self, model: TenantModel) -> Tenant:
        return Tenant(
            id=model.id,
            name=model.name,
            slug=model.slug,
            plan=model.plan,
            is_active=model.is_active,
        )

    def _to_user_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            tenant_id=model.tenant_id,
            email=model.email,
            full_name=model.full_name,
            hashed_password=model.hashed_password,
            role=model.role,
            is_active=model.is_active,
        )

    async def get_tenant_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        stmt = select(TenantModel).where(
            TenantModel.id == tenant_id,
            TenantModel.is_deleted.is_(False),
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_tenant_entity(model) if model else None

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        stmt = select(TenantModel).where(
            TenantModel.slug == slug.lower().strip(),
            TenantModel.is_deleted.is_(False),
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_tenant_entity(model) if model else None

    async def save_tenant(self, tenant: Tenant) -> Tenant:
        stmt = select(TenantModel).where(TenantModel.id == tenant.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()

        if model:
            model.name = tenant.name
            model.slug = tenant.slug
            model.plan = tenant.plan
            model.is_active = tenant.is_active
        else:
            model = TenantModel(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                plan=tenant.plan,
                is_active=tenant.is_active,
            )
            self.session.add(model)

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_tenant_entity(model)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(UserModel).where(
            UserModel.id == user_id,
            UserModel.is_deleted.is_(False),
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_user_entity(model) if model else None

    async def get_user_by_email(self, email: str, tenant_id: Optional[UUID] = None) -> Optional[User]:
        stmt = select(UserModel).where(
            UserModel.email == email.lower().strip(),
            UserModel.is_deleted.is_(False),
        )
        if tenant_id:
            stmt = stmt.where(UserModel.tenant_id == tenant_id)

        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_user_entity(model) if model else None

    async def save_user(self, user: User) -> User:
        stmt = select(UserModel).where(UserModel.id == user.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()

        if model:
            model.email = user.email
            model.full_name = user.full_name
            model.hashed_password = user.hashed_password
            model.role = user.role
            model.is_active = user.is_active
        else:
            model = UserModel(
                id=user.id,
                tenant_id=user.tenant_id,
                email=user.email,
                full_name=user.full_name,
                hashed_password=user.hashed_password,
                role=user.role,
                is_active=user.is_active,
            )
            self.session.add(model)

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_user_entity(model)

