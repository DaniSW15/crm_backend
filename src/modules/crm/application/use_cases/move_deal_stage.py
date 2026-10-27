from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.modules.crm.application.ports.pipeline_repository import PipelineRepository
from src.modules.crm.domain.entities.deal import Deal
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.domain.exceptions import EntityNotFoundException


@dataclass
class MoveDealStageCommand:
    tenant_id: UUID
    deal_id: UUID
    new_stage_id: UUID
    user_id: Optional[UUID] = None


class MoveDealStageUseCase:
    """Caso de uso: Mover una oportunidad a una nueva etapa del embudo comercial."""

    def __init__(
        self,
        deal_repository: DealRepository,
        pipeline_repository: PipelineRepository,
        uow: UnitOfWork,
    ):
        self.deal_repo = deal_repository
        self.pipeline_repo = pipeline_repository
        self.uow = uow

    async def execute(self, cmd: MoveDealStageCommand) -> Deal:
        deal = await self.deal_repo.get_by_id(cmd.deal_id, cmd.tenant_id)
        if not deal:
            raise EntityNotFoundException(f"La oportunidad con ID {cmd.deal_id} no existe.")

        pipeline = await self.pipeline_repo.get_by_id(deal.pipeline_id, cmd.tenant_id)
        if not pipeline:
            raise EntityNotFoundException("El embudo de ventas no existe en esta organización.")
        pipeline.get_stage(cmd.new_stage_id)

        previous_stage_id = deal.stage_id

        # Invocar la lógica de negocio pura en la entidad de dominio
        deal.change_stage(cmd.new_stage_id)

        # Persistir el cambio de estado
        updated_deal = await self.deal_repo.save(deal)

        # Registrar la transición en el historial de analítica
        await self.deal_repo.record_stage_history(
            tenant_id=cmd.tenant_id,
            deal_id=updated_deal.id,
            from_stage_id=previous_stage_id,
            to_stage_id=cmd.new_stage_id,
            changed_by_user_id=cmd.user_id,
        )

        return updated_deal

