"""
FileGate — impone el scope de cada agente A NIVEL TECNICO.

No basta con decirle a un agente "solo escribe en backend/". Un LLM puede
ignorarlo. El FileGate valida cada escritura: si el path resuelto cae fuera de
las rutas permitidas del agente, la operacion se RECHAZA y se le devuelve el
error al modelo (que entonces corrige).

allowed_write son patrones relativos al workspace:
  - "backend/"          -> toda la carpeta backend y subcarpetas
  - "docs/04-arq.md"    -> solo ese fichero
  - "docs/03-design/**" -> glob recursivo

Lectura: todos los agentes pueden leer cualquier cosa dentro del workspace
(necesitan ver el trabajo de los demas). Solo la ESCRITURA esta restringida.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path


class ScopeViolation(Exception):
    """Se lanza cuando un agente intenta escribir fuera de su scope."""


class FileGate:
    def __init__(self, workspace_root: Path, allowed_write: list[str]):
        self.root = workspace_root.resolve()
        self.allowed_write = allowed_write or []

    # ── Resolucion segura de paths ────────────────────────────────────────────
    def resolve(self, rel_path: str) -> Path:
        """Resuelve un path relativo dentro del workspace, evitando escapes (..)."""
        candidate = (self.root / rel_path).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ScopeViolation(
                f"Ruta fuera del workspace: '{rel_path}'. Solo puedes tocar el "
                f"proyecto bajo el workspace."
            )
        return candidate

    def rel(self, rel_path: str) -> str:
        """Devuelve el path normalizado relativo al workspace (con / como separador)."""
        return self.resolve(rel_path).relative_to(self.root).as_posix()

    # ── Comprobacion de escritura ─────────────────────────────────────────────
    def can_write(self, rel_path: str) -> bool:
        norm = self.rel(rel_path)
        for pattern in self.allowed_write:
            if self._match(norm, pattern):
                return True
        return False

    def check_write(self, rel_path: str):
        if not self.can_write(rel_path):
            allowed = ", ".join(self.allowed_write) or "(ninguna)"
            raise ScopeViolation(
                f"PERMISO DENEGADO: no puedes escribir en '{rel_path}'. "
                f"Tu scope de escritura es: {allowed}. "
                f"Cine a tu area de responsabilidad."
            )

    @staticmethod
    def _match(norm: str, pattern: str) -> bool:
        p = pattern.replace("\\", "/")
        # Patron de carpeta: "backend/" cubre "backend/x", "backend/a/b", y "backend"
        if p.endswith("/"):
            prefix = p.rstrip("/")
            return norm == prefix or norm.startswith(prefix + "/")
        # Glob recursivo: "docs/x/**"
        if p.endswith("/**"):
            prefix = p[:-3]
            return norm == prefix or norm.startswith(prefix + "/")
        # Glob normal o match exacto
        return fnmatch.fnmatch(norm, p) or norm == p
