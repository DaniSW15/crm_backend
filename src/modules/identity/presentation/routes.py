from datetime import datetime, timezone

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.core.security import decode_access_token
from src.core.tenant import TenantContext, bearer_scheme, require_authenticated_user
from src.modules.identity.application.use_cases.logout import LogoutUseCase
from src.modules.identity.application.use_cases.get_me import GetMeUseCase
from src.modules.identity.application.use_cases.login import (
    LoginCommand,
    LoginUseCase,
)
from src.modules.identity.application.use_cases.register_tenant import (
    RegisterTenantCommand,
    RegisterTenantUseCase,
)
from src.modules.identity.presentation.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterTenantRequest,
    TenantSummaryResponse,
    UserProfileResponse,
)
from src.shared.domain.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
)

router = APIRouter(prefix="/auth", tags=["Identity & Autenticación"])


@router.post(
    "/register-tenant",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nueva Organización y Usuario Admin",
)
@inject
async def register_tenant(
    request: RegisterTenantRequest,
    use_case: FromDishka[RegisterTenantUseCase],
) -> AuthResponse:
    """
    Onboarding inicial: Registra la empresa (Tenant) y su primer usuario Administrador,
    devolviendo inmediatamente el Token JWT para comenzar a operar.
    """
    cmd = RegisterTenantCommand(
        company_name=request.company_name,
        slug=request.slug,
        admin_full_name=request.admin_full_name,
        admin_email=request.admin_email,
        admin_password=request.admin_password,
    )
    try:
        result = await use_case.execute(cmd)
        return AuthResponse.model_validate(result)
    except BusinessRuleViolationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post(
    "/login/",
    response_model=AuthResponse,
    include_in_schema=False,
)
@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Iniciar sesión con email y contraseña",
)
@inject
async def login(
    request: LoginRequest,
    use_case: FromDishka[LoginUseCase],
) -> AuthResponse:
    """
    Autentica un usuario del CRM y genera un token JWT con claims de seguridad y tenant.
    """
    cmd = LoginCommand(email=request.email, password=request.password)
    try:
        result = await use_case.execute(cmd)
        return AuthResponse.model_validate(result)
    except BusinessRuleViolationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
@router.post("/logout/", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar la sesión actual")
@inject
async def logout(
    use_case: FromDishka[LogoutUseCase],
    auth: TenantContext = Depends(require_authenticated_user),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if bearer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un Bearer Token para cerrar sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # La dependencia de autenticación ya validó firma, identidad, expiración y revocación.
    try:
        payload = decode_access_token(bearer.credentials)
    except ValueError:
        # El token puede vencer entre la dependencia y la ejecución de esta ruta.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await use_case.execute(
        bearer.credentials, datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    )


@router.get("/me/", response_model=UserProfileResponse, include_in_schema=False)
@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Obtener perfil del usuario actual",
)
@inject
async def get_my_profile(
    use_case: FromDishka[GetMeUseCase],
    auth: TenantContext = Depends(require_authenticated_user),
) -> UserProfileResponse:
    """
    Retorna la información del usuario en sesión y la empresa a la que pertenece.
    """
    try:
        result = await use_case.execute(auth.user_id)
        return UserProfileResponse(
            id=result.user.id,
            tenant_id=result.user.tenant_id,
            email=result.user.email,
            full_name=result.user.full_name,
            role=result.user.role,
            is_active=result.user.is_active,
            tenant=TenantSummaryResponse.model_validate(result.tenant),
        )
    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

