from dataclasses import dataclass, field
from typing import List
from uuid import UUID


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

