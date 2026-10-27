from collections.abc import AsyncGenerator
from dishka import Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.config import Settings, get_settings
from src.core.database import async_session_factory, engine
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class CoreProvider(Provider):
    """
    Proveedor base de Dishka para componentes de infraestructura de aplicación y request.
    """
    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        return get_settings()

    @provide(scope=Scope.APP)
    def get_engine(self) -> AsyncEngine:
        return engine

    @provide(scope=Scope.APP)
    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        return async_session_factory

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_unit_of_work(self, session: AsyncSession) -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session)


from src.modules.crm.infrastructure.di import CrmProvider
from src.modules.identity.infrastructure.di import IdentityProvider


def create_container():
    """Crea y configura el contenedor IoC raíz de Dishka."""
    return make_async_container(CoreProvider(), IdentityProvider(), CrmProvider())

