from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise CRM Backend"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:55432/crm_db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Security
    SECRET_KEY: str = "changeme-in-production-super-secret-key"
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, gt=0)

    # CORS Origins (Angular & React local dev ports)
    CORS_ORIGINS: list[str] = [
        "http://localhost:4200",  # Angular CLI
        "http://127.0.0.1:4200",
        "http://localhost:5173",  # React (Vite)
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # React (Next.js / CRA)
        "http://127.0.0.1:3000",
        "http://localhost:5174",
        "http://localhost:8080",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG debe estar desactivado en producción.")
            if self.DB_ECHO:
                raise ValueError("DB_ECHO debe estar desactivado en producción.")
            example_keys = {
                "changeme-in-production-super-secret-key",
                "super-secret-key-change-in-production-1234567890",
            }
            if self.SECRET_KEY.strip() in example_keys or len(self.SECRET_KEY.strip()) < 32:
                raise ValueError("Producción requiere una SECRET_KEY propia de al menos 32 caracteres.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

