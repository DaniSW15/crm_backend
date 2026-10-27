from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.modules.crm.domain.entities.deal import Deal
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.domain.exceptions import EntityNotFoundException


@dataclass
class UpdateDealCommand:
    deal_id: UUID
    tenant_id: UUID
    title: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    expected_close_date: Optional[date] = None
    account_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class UpdateDealUseCase:
    """Caso de uso: Editar los detalles de una oportunidad comercial existente."""

    def __init__(self, deal_repository: DealRepository, uow: UnitOfWork):
        self.deal_repo = deal_repository
        self.uow = uow

    async def execute(self, cmd: UpdateDealCommand) -> Deal:
        async with self.uow:
            deal = await self.deal_repo.get_by_id(cmd.deal_id, cmd.tenant_id)
            if not deal:
                raise EntityNotFoundException(f"La oportunidad con ID '{cmd.deal_id}' no existe.")

            # Invocar la lógica de negocio en la entidad de dominio
            deal.update_details(
                title=cmd.title,
                amount=cmd.amount,
                currency=cmd.currency,
                expected_close_date=cmd.expected_close_date,
                account_id=cmd.account_id,
                contact_id=cmd.contact_id,
                custom_fields=cmd.custom_fields,
            )

            return await self.deal_repo.save(deal)

