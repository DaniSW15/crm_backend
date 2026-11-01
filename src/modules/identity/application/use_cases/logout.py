import hashlib
from datetime import datetime

from src.modules.identity.application.ports.token_revocation import TokenRevocationRepository


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LogoutUseCase:
    def __init__(self, revocations: TokenRevocationRepository):
        self.revocations = revocations

    async def execute(self, token: str, expires_at: datetime) -> None:
        await self.revocations.revoke(token_fingerprint(token), expires_at)
