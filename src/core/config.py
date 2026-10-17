from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise CRM Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:55432/crm_db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Security
    SECRET_KEY: str = "changeme-in-production-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

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


@lru_cache
def get_settings() -> Settings:
    return Settings()

