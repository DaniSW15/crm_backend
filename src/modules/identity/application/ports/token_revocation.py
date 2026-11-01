from abc import ABC, abstractmethod
from datetime import datetime


class TokenRevocationRepository(ABC):
    @abstractmethod
    async def is_revoked(self, token_hash: str) -> bool:
        """Comprueba si la sesión fue cerrada."""
        pass

    @abstractmethod
    async def revoke(self, token_hash: str, expires_at: datetime) -> None:
        """Revoca una sesión de forma persistente e idempotente."""
        pass
