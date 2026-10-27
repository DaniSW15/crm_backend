from typing import Any

from src.core.security import create_access_token, hash_password, verify_password
from src.modules.identity.application.ports.security import PasswordHasher, TokenService


class Pbkdf2PasswordHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        return verify_password(password, hashed_password)


class JwtTokenService(TokenService):
    def create_access_token(self, claims: dict[str, Any]) -> str:
        return create_access_token(claims)
