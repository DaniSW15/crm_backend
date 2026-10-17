from typing import List, Optional
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from src.core.tenant import TenantContext, resolve_tenant_context
from src.modules.crm.application.use_cases.create_deal import (
    CreateDealCommand,
    CreateDealUseCase,
)
from src.modules.crm.application.use_cases.list_deals import (
    ListDealsQuery,
    ListDealsUseCase,
)
from src.modules.crm.application.use_cases.move_deal_stage import (
    MoveDealStageCommand,
    MoveDealStageUseCase,
)
from src.modules.crm.presentation.schemas import (
    DealCreateRequest,
    DealResponse,
    MoveDealStageRequest,
)
from src.shared.domain.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
)

router = APIRouter(prefix="/deals", tags=["CRM - Deals / Oportunidades"])


@router.post("", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_deal(
    request: DealCreateRequest,
    use_case: FromDishka[CreateDealUseCase],
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> DealResponse:
    """Crea una nueva oportunidad comercial para el tenant actual."""
    cmd = CreateDealCommand(
        tenant_id=tenant.tenant_id,
        title=request.title,
        amount=request.amount,
        currency=request.currency,
        pipeline_id=request.pipeline_id,
        stage_id=request.stage_id,
        owner_id=request.owner_id,
        account_id=request.account_id,
        contact_id=request.contact_id,
        expected_close_date=request.expected_close_date,
        custom_fields=request.custom_fields,
    )
    try:
        deal = await use_case.execute(cmd)
        return DealResponse.model_validate(deal)
    except BusinessRuleViolationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad: el ID de cuenta, contacto, pipeline o propietario especificado no existe.",
        )


@router.get("", response_model=List[DealResponse])
@inject
async def list_deals(
    use_case: FromDishka[ListDealsUseCase],
    tenant: TenantContext = Depends(resolve_tenant_context),
    pipeline_id: Optional[UUID] = Query(None, description="Filtrar por embudo"),
    stage_id: Optional[UUID] = Query(None, description="Filtrar por etapa"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado (OPEN, WON, LOST)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[DealResponse]:
    """Lista las oportunidades comerciales del tenant con soporte de filtros."""
    query = ListDealsQuery(
        tenant_id=tenant.tenant_id,
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    deals = await use_case.execute(query)
    return [DealResponse.model_validate(d) for d in deals]


@router.post("/{deal_id}/move-stage", response_model=DealResponse)
@inject
async def move_deal_stage(
    deal_id: UUID,
    request: MoveDealStageRequest,
    use_case: FromDishka[MoveDealStageUseCase],
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> DealResponse:
    """Mueve una oportunidad a una nueva etapa del embudo comercial."""
    cmd = MoveDealStageCommand(
        tenant_id=tenant.tenant_id,
        deal_id=deal_id,
        new_stage_id=request.new_stage_id,
        user_id=tenant.user_id,
    )
    try:
        updated_deal = await use_case.execute(cmd)
        return DealResponse.model_validate(updated_deal)
    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except BusinessRuleViolationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

