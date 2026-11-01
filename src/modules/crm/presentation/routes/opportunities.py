from fastapi import APIRouter, status

from src.modules.crm.presentation.routes.deals import create_deal, list_deals
from src.modules.crm.presentation.schemas import DealResponse

router = APIRouter(prefix="/opportunities", tags=["CRM - Oportunidades"])

for path in ("/", ""):
    router.add_api_route(
        path,
        list_deals,
        methods=["GET"],
        response_model=list[DealResponse],
        summary="Listar oportunidades",
        include_in_schema=path == "/",
    )
    router.add_api_route(
        path,
        create_deal,
        methods=["POST"],
        response_model=DealResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Crear oportunidad",
        include_in_schema=path == "/",
    )
