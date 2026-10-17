from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.modules.crm.domain.entities.deal import Deal


@dataclass
class ListDealsQuery:
    tenant_id: UUID
    pipeline_id: Optional[UUID] = None
    stage_id: Optional[UUID] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0


class ListDealsUseCase:
    """Caso de uso: Listar y filtrar oportunidades de venta."""

    def __init__(self, deal_repository: DealRepository):
        self.deal_repo = deal_repository

    async def execute(self, query: ListDealsQuery) -> List[Deal]:
        return await self.deal_repo.list(
            tenant_id=query.tenant_id,
            pipeline_id=query.pipeline_id,
            stage_id=query.stage_id,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )

