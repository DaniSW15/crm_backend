from abc import ABC, abstractmethod
from typing import Any


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str:
        pass

    @abstractmethod
    def verify(self, password: str, hashed_password: str) -> bool:
        pass


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, claims: dict[str, Any]) -> str:
        pass
