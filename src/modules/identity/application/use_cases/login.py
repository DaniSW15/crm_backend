from dataclasses import dataclass

from src.modules.identity.application.dto import AuthResult
from src.modules.identity.application.ports.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.application.ports.security import PasswordHasher, TokenService
from src.shared.domain.exceptions import BusinessRuleViolationException


@dataclass
class LoginCommand:
    email: str
    password: str


class LoginUseCase:
    """Caso de uso: Autenticar a un usuario y generar su token JWT de sesión."""

    def __init__(
        self,
        identity_repo: IdentityRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ):
        self.identity_repo = identity_repo
        self.password_hasher = password_hasher
        self.token_service = token_service

    async def execute(self, cmd: LoginCommand) -> AuthResult:
        clean_email = cmd.email.lower().strip()
        user = await self.identity_repo.get_user_by_email(clean_email)

        if not user or not user.is_active:
            raise BusinessRuleViolationException("Credenciales inválidas o usuario inactivo.")

        if not self.password_hasher.verify(cmd.password, user.hashed_password):
            raise BusinessRuleViolationException("Credenciales inválidas.")

        # Generar token JWT con los claims necesarios
        token = self.token_service.create_access_token(
            {
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id),
                "email": user.email,
                "role": user.role,
            }
        )

        return AuthResult(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        )

