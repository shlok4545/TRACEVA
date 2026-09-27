import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = (BASE_DIR / "app.db").resolve()


class Settings(BaseSettings):
    app_name: str = "TRACEVA API"
    app_env: str = "development"
    database_url: str = f"sqlite:///{DATABASE_PATH.as_posix()}"
    secret_key: str = os.getenv("TRACEVA_SECRET_KEY", "traceva-dev-secret-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = os.getenv("TRACEVA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174")

    class Config:
        env_file = BASE_DIR / ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


class AppConfig(BaseModel):
    app_name: str
    app_env: str
    database_url: str
    cors_origins: list[str]


def get_app_config() -> AppConfig:
    settings = get_settings()
    return AppConfig(
        app_name=settings.app_name,
        app_env=settings.app_env,
        database_url=settings.database_url,
        cors_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    )

