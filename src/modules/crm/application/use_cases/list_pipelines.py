from typing import List
from uuid import UUID

from src.modules.crm.application.ports.pipeline_repository import PipelineRepository
from src.modules.crm.domain.entities.pipeline import Pipeline


class ListPipelinesUseCase:
    """Caso de uso: Obtener todos los embudos comerciales y sus etapas para el tenant actual."""

    def __init__(self, pipeline_repo: PipelineRepository):
        self.pipeline_repo = pipeline_repo

    async def execute(self, tenant_id: UUID) -> List[Pipeline]:
        return await self.pipeline_repo.list_by_tenant(tenant_id=tenant_id)

