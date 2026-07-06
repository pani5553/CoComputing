from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: Optional[str] = None

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # CORS
    frontend_url: str = "http://localhost:5173"

    # App
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def jwt_expire_seconds(self) -> int:
        return self.jwt_expire_days * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
