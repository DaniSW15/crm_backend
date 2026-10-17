from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.ports.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.application.use_cases.get_me import GetMeUseCase
from src.modules.identity.application.use_cases.login import LoginUseCase
from src.modules.identity.application.use_cases.register_tenant import (
    RegisterTenantUseCase,
)
from src.modules.identity.infrastructure.repositories import (
    SqlAlchemyIdentityRepository,
)


class IdentityProvider(Provider):
    """
    Proveedor de inyección de dependencias (Dishka) para el módulo Identity.
    """
    scope = Scope.REQUEST

    @provide
    def get_identity_repository(self, session: AsyncSession) -> IdentityRepository:
        return SqlAlchemyIdentityRepository(session=session)

    @provide
    def get_register_tenant_use_case(self, repo: IdentityRepository) -> RegisterTenantUseCase:
        return RegisterTenantUseCase(identity_repo=repo)

    @provide
    def get_login_use_case(self, repo: IdentityRepository) -> LoginUseCase:
        return LoginUseCase(identity_repo=repo)

    @provide
    def get_me_use_case(self, repo: IdentityRepository) -> GetMeUseCase:
        return GetMeUseCase(identity_repo=repo)

