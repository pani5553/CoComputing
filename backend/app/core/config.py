import logging
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: str

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
        # utf-8-sig strips a leading BOM if the .env file was saved by an
        # editor that adds one (e.g. Windows Notepad) — without this, the
        # first variable in the file is silently renamed to "﻿VARNAME"
        # and Settings() fails with "field required" for that variable.
        env_file_encoding="utf-8-sig",
        case_sensitive=False,
        # Real deployment .env files accumulate variables (e.g. CORS_ORIGINS)
        # that predate or exceed the current Settings fields. `extra="ignore"`
        # would keep config loading resilient but silently swallow the extra
        # keys with no visibility at all — a typo in a variable that backs a
        # field with a default (e.g. "ENVIRONEMNT" instead of "ENVIRONMENT")
        # would silently degrade to that field's default instead of failing
        # loudly (EN-MAYOR-01, docs/05-review.md 2026-07-09). `extra="allow"`
        # keeps the same resilience (no hard failure on unrecognized keys)
        # while making them inspectable via `model_extra` after instantiation
        # — see the warning logged in get_settings() below.
        extra="allow",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def jwt_expire_seconds(self) -> int:
        return self.jwt_expire_days * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    instance = Settings()
    # With extra="allow", unrecognized env/`.env` keys no longer raise —
    # surface them as a startup warning instead, so a typo in a field with a
    # default (in particular ENVIRONMENT) or a genuinely obsolete variable is
    # still visible in deploy logs (EN-MAYOR-01, docs/05-review.md 2026-07-09),
    # without turning it into a hard failure.
    extra_keys = sorted((instance.model_extra or {}).keys())
    if extra_keys:
        logger.warning(
            "Settings() recibió %d variable(s) de entorno no reconocidas por "
            "el modelo (extra='allow'): %s. Revisa si es un typo de un campo "
            "real (p. ej. ENVIRONMENT) o una variable obsoleta que debería "
            "eliminarse.",
            len(extra_keys),
            ", ".join(extra_keys),
        )
    return instance


settings = get_settings()
