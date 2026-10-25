from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.modules.crm.domain.entities.pipeline import Pipeline


class PipelineRepository(ABC):
    """
    Puerto (Interface) del repositorio de Embudos de Venta (Pipelines).
    """

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID) -> List[Pipeline]:
        """Lista todos los embudos comerciales activos del tenant junto con sus etapas ordenadas."""
        pass

    @abstractmethod
    async def get_by_id(self, pipeline_id: UUID, tenant_id: UUID) -> Optional[Pipeline]:
        """Obtiene un embudo con sus etapas."""
        pass

