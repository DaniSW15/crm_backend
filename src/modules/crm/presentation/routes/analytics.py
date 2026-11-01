from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from src.core.tenant import TenantContext, resolve_tenant_context
from src.modules.crm.application.use_cases.analytics_summary import AnalyticsSummaryUseCase
from src.modules.crm.presentation.analytics_schemas import AnalyticsSummaryResponse

router = APIRouter(prefix="/analytics", tags=["CRM - Indicadores"])


@router.get("/summary", response_model=AnalyticsSummaryResponse, include_in_schema=False)
@router.get("/summary/", response_model=AnalyticsSummaryResponse, summary="Indicadores de la organización")
@inject
async def analytics_summary(
    use_case: FromDishka[AnalyticsSummaryUseCase],
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> AnalyticsSummaryResponse:
    result = await use_case.execute(tenant_id=tenant.tenant_id)
    return AnalyticsSummaryResponse.model_validate(result)
