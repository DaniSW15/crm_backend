import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.modules.crm.application.ports.pipeline_repository import PipelineRepository
from src.modules.crm.domain.entities.deal import Deal
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.domain.exceptions import EntityNotFoundException


@dataclass
class CreateDealCommand:
    tenant_id: UUID
    title: str
    amount: Decimal
    currency: str
    pipeline_id: UUID
    stage_id: UUID
    owner_id: UUID
    account_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    expected_close_date: Optional[date] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CreateDealUseCase:
    """Caso de uso: Crear una nueva oportunidad comercial."""

    def __init__(
        self,
        deal_repository: DealRepository,
        pipeline_repository: PipelineRepository,
        uow: UnitOfWork,
    ):
        self.deal_repo = deal_repository
        self.pipeline_repo = pipeline_repository
        self.uow = uow

    async def execute(self, cmd: CreateDealCommand) -> Deal:
        async with self.uow:
            pipeline = await self.pipeline_repo.get_by_id(cmd.pipeline_id, cmd.tenant_id)
            if not pipeline:
                raise EntityNotFoundException("El embudo de ventas no existe en esta organización.")
            pipeline.get_stage(cmd.stage_id)

            deal = Deal(
                id=uuid.uuid4(),
                tenant_id=cmd.tenant_id,
                title=cmd.title,
                amount=cmd.amount,
                currency=cmd.currency.upper(),
                pipeline_id=cmd.pipeline_id,
                stage_id=cmd.stage_id,
                owner_id=cmd.owner_id,
                status="OPEN",
                account_id=cmd.account_id,
                contact_id=cmd.contact_id,
                expected_close_date=cmd.expected_close_date,
                custom_fields=cmd.custom_fields or {},
            )

            saved_deal = await self.deal_repo.save(deal)

            # Registrar primera etapa en el historial
            await self.deal_repo.record_stage_history(
                tenant_id=cmd.tenant_id,
                deal_id=saved_deal.id,
                from_stage_id=None,
                to_stage_id=cmd.stage_id,
                changed_by_user_id=cmd.owner_id,
                duration_seconds=0,
            )

            return saved_deal

