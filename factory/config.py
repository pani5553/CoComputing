"""Settings de la factoria, cargadas desde .env / entorno."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv es opcional; las vars pueden venir del entorno


ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    anthropic_api_key: str
    model_default: str
    model_director: str
    max_iterations: int
    workspace_dir: Path
    runs_dir: Path
    dry_run: bool = False

    @classmethod
    def load(cls, dry_run: bool = False) -> "Settings":
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model_default=os.getenv("FACTORY_MODEL", "claude-sonnet-4-6"),
            # Por defecto los directores tambien usan Sonnet (barato). Sube a Opus
            # en .env (FACTORY_MODEL_DIRECTOR=claude-opus-4-8) si quieres mas calidad
            # en vision/arquitectura a cambio de ~5x el coste de esos 3 roles.
            model_director=os.getenv("FACTORY_MODEL_DIRECTOR", "claude-sonnet-4-6"),
            max_iterations=int(os.getenv("FACTORY_MAX_ITERATIONS", "25")),
            workspace_dir=ROOT / "workspace",
            runs_dir=ROOT / "runs",
            dry_run=dry_run,
        )

    def require_key(self):
        if not self.dry_run and not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY no esta configurada. Crea un .env (ver .env.example) "
                "o usa --dry-run para probar el flujo sin llamar al API."
            )
