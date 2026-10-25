from uuid import UUID

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.shared.domain.exceptions import EntityNotFoundException


class DeleteDealUseCase:
    """Caso de uso: Eliminar una oportunidad comercial (Requiere permisos ADMIN o DEV)."""

    def __init__(self, deal_repository: DealRepository):
        self.deal_repo = deal_repository

    async def execute(self, deal_id: UUID, tenant_id: UUID) -> None:
        deleted = await self.deal_repo.delete(deal_id=deal_id, tenant_id=tenant_id)
        if not deleted:
            raise EntityNotFoundException(f"La oportunidad con ID '{deal_id}' no existe.")

