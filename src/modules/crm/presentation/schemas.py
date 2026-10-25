from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DealCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, example="Licencia Anual Acme Corp")
    amount: Decimal = Field(..., ge=0, example=15000.00)
    currency: str = Field(default="USD", min_length=3, max_length=3, example="USD")
    pipeline_id: UUID = Field(..., example="a0000000-0000-0000-0000-000000000001")
    stage_id: UUID = Field(..., example="b0000000-0000-0000-0000-000000000001")
    owner_id: UUID = Field(..., example="c0000000-0000-0000-0000-000000000001")
    account_id: Optional[UUID] = Field(default=None, example=None)
    contact_id: Optional[UUID] = Field(default=None, example=None)
    expected_close_date: Optional[date] = Field(default=None, example="2026-12-31")
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, example={})


class MoveDealStageRequest(BaseModel):
    new_stage_id: UUID = Field(..., example="b0000000-0000-0000-0000-000000000002")


class DealUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200, example="Licencia Anual Acme Corp (Renegociada)")
    amount: Optional[Decimal] = Field(None, ge=0, example=18000.00)
    currency: Optional[str] = Field(None, min_length=3, max_length=3, example="USD")
    expected_close_date: Optional[date] = Field(None, example="2026-12-31")
    account_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class DealResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    amount: Decimal
    currency: str
    pipeline_id: UUID
    stage_id: UUID
    owner_id: UUID
    status: str
    account_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    expected_close_date: Optional[date] = None
    actual_close_date: Optional[datetime] = None
    lost_reason: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class PipelineStageResponse(BaseModel):
    id: UUID
    pipeline_id: UUID
    name: str
    order: int
    win_probability: float
    days_until_stale: int
    is_won_stage: bool
    is_lost_stage: bool

    model_config = ConfigDict(from_attributes=True)


class PipelineResponse(BaseModel):
    id: UUID
    name: str
    is_default: bool
    is_active: bool
    stages: list[PipelineStageResponse] = []

    model_config = ConfigDict(from_attributes=True)

