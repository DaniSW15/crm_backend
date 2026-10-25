from typing import List
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.core.tenant import TenantContext, resolve_tenant_context
from src.modules.crm.application.use_cases.list_pipelines import ListPipelinesUseCase
from src.modules.crm.presentation.schemas import (
    PipelineResponse,
    PipelineStageResponse,
)

router = APIRouter(prefix="/pipelines", tags=["CRM - Embudos de Venta (Pipelines)"])


@router.get(
    "",
    response_model=List[PipelineResponse],
    summary="Listar embudos de venta y sus etapas ordenadas",
)
@inject
async def list_pipelines(
    use_case: FromDishka[ListPipelinesUseCase],
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> List[PipelineResponse]:
    """
    Retorna todos los embudos de venta del tenant con sus etapas ordenadas (Kanban).
    Ideal para que el frontend (Angular / React) pinte las columnas del embudo comercial.
    """
    pipelines = await use_case.execute(tenant_id=tenant.tenant_id)
    return [
        PipelineResponse(
            id=p.id,
            name=p.name,
            is_default=p.is_default,
            is_active=p.is_active,
            stages=[
                PipelineStageResponse(
                    id=s.id,
                    pipeline_id=s.pipeline_id,
                    name=s.name,
                    order=s.order,
                    win_probability=s.win_probability,
                    days_until_stale=s.days_until_stale,
                    is_won_stage=s.is_won_stage,
                    is_lost_stage=s.is_lost_stage,
                )
                for s in p.stages
            ],
        )
        for p in pipelines
    ]

