from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import get_settings
from src.core.security import decode_access_token
from src.modules.identity.application.ports.token_revocation import TokenRevocationRepository
from src.modules.identity.application.use_cases.logout import token_fingerprint

settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False)


@inject
async def check_token_revocation(
    revocations: FromDishka[TokenRevocationRepository],
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> None:
    if not bearer or not bearer.credentials:
        return
    try:
        # Los tokens malformados o vencidos no deben consultar la base de datos.
        decode_access_token(bearer.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if await revocations.is_revoked(token_fingerprint(bearer.credentials)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión fue cerrada. Inicia sesión de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@dataclass(frozen=True)
class TenantContext:
    """
    Contexto de multi-inquilino de la petición HTTP actual.
    Contiene el ID del tenant, del usuario autenticado y su rol comercial.
    """
    tenant_id: UUID
    user_id: Optional[UUID] = None
    role: Optional[str] = None


def resolve_tenant_context(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_tenant_id: Optional[str] = Header(
        default=None,
        alias="X-Tenant-ID",
        description="Ignorado: la organización se obtiene exclusivamente del JWT.",
    ),
    x_user_id: Optional[str] = Header(
        default=None,
        alias="X-User-ID",
        description="Ignorado: el usuario se obtiene exclusivamente del JWT.",
    ),
    _revocation_check: None = Depends(check_token_revocation),
) -> TenantContext:
    """
    Valida el JWT y obtiene tenant, usuario y rol exclusivamente de sus claims.
    DEBUG y los headers de organización nunca autentican una petición.
    """
    # 1. Intentar validar por Bearer JWT Token
    if bearer and bearer.credentials:
        try:
            payload = decode_access_token(bearer.credentials)
            tenant_uuid = UUID(payload["tenant_id"])
            user_uuid = UUID(payload["sub"])
            role = payload.get("role")
            return TenantContext(tenant_id=tenant_uuid, user_id=user_uuid, role=role)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación inválido.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticación requerida. Envía un Bearer Token válido.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_authenticated_user(
    tenant_context: TenantContext = Depends(resolve_tenant_context),
) -> TenantContext:
    """Dependencia estricta: exige que el usuario esté identificado (user_id no nulo)."""
    if not tenant_context.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un usuario autenticado para realizar esta acción.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return tenant_context


def require_roles(*allowed_roles: str):
    """
    Control de acceso basado en roles (RBAC).
    Verifica que el usuario autenticado posea uno de los roles autorizados.
    Ejemplo: require_roles("ADMIN", "DEV")
    """
    def role_checker(context: TenantContext = Depends(require_authenticated_user)) -> TenantContext:
        user_role = (context.role or "").upper()
        allowed = {r.upper() for r in allowed_roles}
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: tu rol '{user_role or 'SIN_ROL'}' no tiene permiso para esta operación. Roles requeridos: {', '.join(allowed)}.",
            )
        return context

    return role_checker
