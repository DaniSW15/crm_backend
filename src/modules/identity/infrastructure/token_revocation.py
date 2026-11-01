from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.identity.application.ports.token_revocation import TokenRevocationRepository
from src.modules.identity.infrastructure.session_models import RevokedTokenModel


class SqlAlchemyTokenRevocationRepository(TokenRevocationRepository):
    """Cada operación usa una sesión propia para no iniciar la UOW del caso de uso."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def is_revoked(self, token_hash: str) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(select(RevokedTokenModel.token_hash).where(
                RevokedTokenModel.token_hash == token_hash
            ))
            return result.scalar_one_or_none() is not None

    async def revoke(self, token_hash: str, expires_at: datetime) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                try:
                    async with session.begin_nested():
                        session.add(RevokedTokenModel(token_hash=token_hash, expires_at=expires_at))
                        await session.flush()
                except IntegrityError:
                    # Una petición concurrente pudo revocar el mismo token primero.
                    result = await session.execute(select(RevokedTokenModel.token_hash).where(
                        RevokedTokenModel.token_hash == token_hash
                    ))
                    if result.scalar_one_or_none() is None:
                        raise
