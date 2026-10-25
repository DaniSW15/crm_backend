from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.modules.crm.domain.entities.deal import Deal


class DealRepository(ABC):
    """
    Puerto (Interface) del repositorio de Oportunidades (Deals).
    Define las operaciones de persistencia sin acoplarse a SQLAlchemy ni a la BD.
    """

    @abstractmethod
    async def get_by_id(self, deal_id: UUID, tenant_id: UUID) -> Optional[Deal]:
        """Obtiene un trato por su ID asegurando el aislamiento del tenant."""
        pass

    @abstractmethod
    async def list(
        self,
        tenant_id: UUID,
        pipeline_id: Optional[UUID] = None,
        stage_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Deal]:
        """Lista oportunidades filtradas con paginación."""
        pass

    @abstractmethod
    async def save(self, deal: Deal) -> Deal:
        """Crea o actualiza una oportunidad comercial."""
        pass

    @abstractmethod
    async def record_stage_history(
        self,
        tenant_id: UUID,
        deal_id: UUID,
        from_stage_id: Optional[UUID],
        to_stage_id: UUID,
        changed_by_user_id: Optional[UUID] = None,
        duration_seconds: Optional[int] = None,
    ) -> None:
        """Registra una transición de etapa inmutable para auditoría y analítica."""
        pass

    @abstractmethod
    async def delete(self, deal_id: UUID, tenant_id: UUID) -> bool:
        """Elimina (borrado lógico) una oportunidad comercial."""
        pass

