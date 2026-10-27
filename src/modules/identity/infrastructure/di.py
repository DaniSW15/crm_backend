from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.ports.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.application.use_cases.get_me import GetMeUseCase
from src.modules.identity.application.ports.security import PasswordHasher, TokenService
from src.modules.identity.application.use_cases.login import LoginUseCase
from src.modules.identity.application.use_cases.register_tenant import (
    RegisterTenantUseCase,
)
from src.modules.identity.infrastructure.repositories import (
    SqlAlchemyIdentityRepository,
)
from src.modules.identity.infrastructure.security import Pbkdf2PasswordHasher, JwtTokenService
from src.shared.application.unit_of_work import UnitOfWork


class IdentityProvider(Provider):
    """
    Proveedor de inyección de dependencias (Dishka) para el módulo Identity.
    """
    scope = Scope.REQUEST

    @provide
    def get_identity_repository(self, session: AsyncSession) -> IdentityRepository:
        return SqlAlchemyIdentityRepository(session=session)

    @provide
    def get_password_hasher(self) -> PasswordHasher:
        return Pbkdf2PasswordHasher()

    @provide
    def get_token_service(self) -> TokenService:
        return JwtTokenService()

    @provide
    def get_register_tenant_use_case(
        self,
        repo: IdentityRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        uow: UnitOfWork,
    ) -> RegisterTenantUseCase:
        return RegisterTenantUseCase(
            identity_repo=repo,
            password_hasher=password_hasher,
            token_service=token_service,
            uow=uow,
        )

    @provide
    def get_login_use_case(
        self,
        repo: IdentityRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> LoginUseCase:
        return LoginUseCase(
            identity_repo=repo, password_hasher=password_hasher, token_service=token_service
        )

    @provide
    def get_me_use_case(self, repo: IdentityRepository) -> GetMeUseCase:
        return GetMeUseCase(identity_repo=repo)

