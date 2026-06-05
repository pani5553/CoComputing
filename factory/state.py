"""
ProjectState — el "blackboard" compartido del equipo.

Persiste en workspace/project_state.json. Guarda:
  - brief:     el encargo del cliente
  - handoffs:  cadena de traspasos entre agentes (quien -> quien, resumen, artefactos)
  - artifacts: ficheros creados, agrupados por agente
  - usage:     tokens y coste acumulados

Cada agente, antes de trabajar, recibe un resumen compacto (context_digest) del
estado actual: que se ha hecho, que artefactos existen y el ultimo handoff. Asi
sabe sobre que construir sin tener que leerse todo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Handoff:
    from_role: str
    to_role: str
    summary: str
    artifacts: list[str] = field(default_factory=list)
    ts: str = field(default_factory=_now)


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost_usd: float = 0.0

    def add(self, other: "Usage"):
        self.tokens_in += other.tokens_in
        self.tokens_out += other.tokens_out
        self.cache_read += other.cache_read
        self.cache_write += other.cache_write
        self.cost_usd = round(self.cost_usd + other.cost_usd, 6)


class ProjectState:
    def __init__(self, workspace_root: Path, brief: str = ""):
        self.root = workspace_root
        self.brief = brief
        self.handoffs: list[Handoff] = []
        self.artifacts: dict[str, list[str]] = {}
        self.usage = Usage()
        self.started_at = _now()

    @property
    def path(self) -> Path:
        return self.root / "project_state.json"

    # ── Mutaciones ────────────────────────────────────────────────────────────
    def record_artifacts(self, role: str, files: list[str]):
        bucket = self.artifacts.setdefault(role, [])
        for f in files:
            if f not in bucket:
                bucket.append(f)

    def add_handoff(self, from_role: str, to_role: str, summary: str, artifacts: list[str]):
        self.handoffs.append(Handoff(from_role, to_role, summary, artifacts))

    def add_usage(self, usage: Usage):
        self.usage.add(usage)

    # ── Vista para el agente ──────────────────────────────────────────────────
    def context_digest(self) -> str:
        """Resumen compacto del estado para inyectar en el contexto del siguiente agente."""
        lines = ["## Estado actual del proyecto", ""]
        if not self.handoffs:
            lines.append("Eres el PRIMER agente. Aun no hay trabajo previo.")
            return "\n".join(lines)

        lines.append("### Trabajo ya realizado (en orden):")
        for h in self.handoffs:
            arts = ", ".join(h.artifacts) if h.artifacts else "(sin ficheros)"
            lines.append(f"- **{h.from_role}**: {h.summary}")
            lines.append(f"  - artefactos: {arts}")

        last = self.handoffs[-1]
        lines += [
            "",
            f"### Handoff mas reciente -> para ti ({last.to_role}):",
            last.summary,
        ]
        all_files = sorted({f for files in self.artifacts.values() for f in files})
        if all_files:
            lines += ["", "### Todos los ficheros existentes en el proyecto:"]
            lines += [f"- {f}" for f in all_files]
        return "\n".join(lines)

    # ── Persistencia ──────────────────────────────────────────────────────────
    def save(self):
        data = {
            "brief": self.brief,
            "started_at": self.started_at,
            "saved_at": _now(),
            "usage": asdict(self.usage),
            "handoffs": [asdict(h) for h in self.handoffs],
            "artifacts": self.artifacts,
        }
        self.root.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
