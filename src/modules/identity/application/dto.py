from dataclasses import dataclass
from uuid import UUID


@dataclass
class AuthResult:
    access_token: str
    token_type: str
    user_id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: str
