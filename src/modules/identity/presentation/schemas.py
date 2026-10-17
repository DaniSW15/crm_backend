from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterTenantRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=150, example="Acme Corporation")
    slug: str = Field(..., min_length=2, max_length=100, example="acme-corp")
    admin_full_name: str = Field(..., min_length=2, max_length=150, example="Carlos García")
    admin_email: str = Field(..., example="carlos@acme.com")
    admin_password: str = Field(..., min_length=6, max_length=100, example="Password123!")


class LoginRequest(BaseModel):
    email: str = Field(..., example="admin@democrm.com")
    password: str = Field(..., example="admin123")


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TenantSummaryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    tenant: TenantSummaryResponse

    model_config = ConfigDict(from_attributes=True)

