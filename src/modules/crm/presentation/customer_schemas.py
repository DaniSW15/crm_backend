from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    industry: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    annual_revenue: Decimal | None = Field(None, ge=0, max_digits=15, decimal_places=2)
    owner_id: UUID | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomerUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    industry: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    annual_revenue: Decimal | None = Field(None, ge=0, max_digits=15, decimal_places=2)
    owner_id: UUID | None = None
    custom_fields: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def reject_required_nulls(cls, value):
        if isinstance(value, dict) and any(key in value and value[key] is None for key in ("name", "custom_fields")):
            raise ValueError("El nombre y los campos personalizados no pueden ser nulos.")
        return value


class CustomerResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    industry: str | None = None
    website: str | None = None
    phone: str | None = None
    annual_revenue: Decimal | None = None
    owner_id: UUID | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
