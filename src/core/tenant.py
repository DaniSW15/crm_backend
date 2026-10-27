from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import get_settings
from src.core.security import decode_access_token

settings = get_settings()
DEFAULT_DEV_TENANT = "00000000-0000-0000-0000-000000000001"
DEFAULT_DEV_USER = "00000000-0000-0000-0000-000000000002"

bearer_scheme = HTTPBearer(auto_error=False)


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
        description="UUID de la organización / tenant (solo en DEBUG)",
    ),
    x_user_id: Optional[str] = Header(
        default=None,
        alias="X-User-ID",
        description="UUID del usuario (solo en DEBUG)",
    ),
) -> TenantContext:
    """
    Resuelve el tenant y usuario actual:
    1. Si viene Bearer JWT token, lo valida y extrae claims de seguridad (tenant_id, sub, role).
    2. Solo en DEBUG, permite headers X-Tenant-ID / X-User-ID o valores demo.
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

    # 2. Los headers de desarrollo nunca autentican peticiones en producción.
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Envía un Bearer Token válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    effective_tenant_id = x_tenant_id or DEFAULT_DEV_TENANT
    try:
        tenant_uuid = UUID(effective_tenant_id)
        user_uuid = UUID(x_user_id or DEFAULT_DEV_USER)
        return TenantContext(tenant_id=tenant_uuid, user_id=user_uuid, role="ADMIN")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El 'X-Tenant-ID' o 'X-User-ID' provisto no es un UUID válido.",
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
