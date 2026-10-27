from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from src.shared.application.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction: AsyncSessionTransaction | None = None

    async def __aenter__(self) -> Self:
        self._transaction = self.session.begin()
        await self._transaction.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._transaction is None:
            raise RuntimeError("La unidad de trabajo no ha iniciado una transacción.")
        try:
            await self._transaction.__aexit__(exc_type, exc_value, traceback)
        finally:
            self._transaction = None
