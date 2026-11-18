"""Centralised settings loaded from .env via pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ammu:Salija1999@localhost:5432/doc_intel"

    # LLM (Phase 4)
    GROQ_API_KEY: str = "replace_me"
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # Auth (Phase 3)
    JWT_SECRET_KEY: str = "dev-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Object storage
    STORAGE_ENDPOINT_URL: str = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET_NAME: str = "docintel"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ML
    MODEL_DIR: str = "./backend/ml_models"

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
