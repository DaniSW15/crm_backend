from dataclasses import dataclass, field
from typing import List
from uuid import UUID

from src.shared.domain.exceptions import BusinessRuleViolationException

@dataclass
class PipelineStage:
    id: UUID
    pipeline_id: UUID
    name: str
    order: int
    win_probability: float = 0.0
    days_until_stale: int = 14
    is_won_stage: bool = False
    is_lost_stage: bool = False


@dataclass
class Pipeline:
    id: UUID
    tenant_id: UUID
    name: str
    is_default: bool = False
    is_active: bool = True
    stages: List[PipelineStage] = field(default_factory=list)

    def get_stage(self, stage_id: UUID) -> PipelineStage:
        if not self.is_active:
            raise BusinessRuleViolationException("El embudo de ventas no está activo.")
        for stage in self.stages:
            if stage.id == stage_id and stage.pipeline_id == self.id:
                return stage
        raise BusinessRuleViolationException("La etapa no pertenece al embudo de ventas indicado.")

