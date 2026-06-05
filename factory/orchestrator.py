"""
Orchestrator — corre el pipeline completo de principio a fin (modo autonomo).

Para cada rol del PIPELINE:
  1. Crea el Agent con su scope.
  2. Lo ejecuta (lee trabajo previo -> produce artefactos -> finish).
  3. Registra handoff + artefactos + uso en el ProjectState.
  4. Guarda el estado y muestra progreso.

Al final imprime un resumen: ficheros generados, coste total y duracion.
"""
from __future__ import annotations

import time
from pathlib import Path

from .agent import Agent
from .llm import LLMClient
from .pipeline import PIPELINE
from .roles import ROLES
from .state import ProjectState


class Orchestrator:
    def __init__(self, settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    def run(self, brief: str, only: list[str] | None = None) -> ProjectState:
        ws = self.settings.workspace_dir
        ws.mkdir(parents=True, exist_ok=True)
        state = ProjectState(ws, brief=brief)

        roles_to_run = only if only else PIPELINE
        total = len(roles_to_run)
        mode = "DRY-RUN (sin API)" if self.settings.dry_run else "AUTONOMO"

        print("\n" + "=" * 70)
        print(f"  AGENT FACTORY — modo {mode}")
        print(f"  workspace: {ws}")
        print(f"  pipeline:  {total} agentes")
        print("=" * 70 + "\n")

        t0 = time.time()
        prev = "cliente"
        for i, role_id in enumerate(roles_to_run, 1):
            spec = ROLES[role_id]
            print(f"[{i}/{total}] {spec.emoji}  {spec.title}  ({spec.level}) ...", flush=True)

            agent = Agent(spec, self.settings, ws, state, self.llm)
            result = agent.run()

            summary = result.finished.summary if result.finished else result.text or "(sin resumen)"
            handoff = result.finished.handoff if result.finished else "(no llamo finish)"
            state.record_artifacts(role_id, result.artifacts)
            state.add_handoff(prev, role_id, summary, result.artifacts)
            state.add_usage(result.usage)
            state.save()

            arts = ", ".join(result.artifacts) if result.artifacts else "(ninguno)"
            print(f"      -> {len(result.artifacts)} artefacto(s): {arts}")
            if not self.settings.dry_run:
                print(f"      -> {result.iterations} iteraciones | "
                      f"${result.usage.cost_usd:.4f} | stop={result.stopped_reason}")
            if not result.finished:
                print(f"      [!] el agente no llamo finish() (stop={result.stopped_reason})")
            print(f"      handoff: {handoff[:120]}{'...' if len(handoff) > 120 else ''}\n")
            prev = role_id

        dur = time.time() - t0
        self._summary(state, dur)
        return state

    def _summary(self, state: ProjectState, dur: float):
        all_files = sorted({f for files in state.artifacts.values() for f in files})
        print("=" * 70)
        print("  ENTREGA COMPLETADA")
        print("=" * 70)
        print(f"  ficheros generados: {len(all_files)}")
        for f in all_files:
            print(f"    - {f}")
        print(f"\n  duracion: {dur:.1f}s")
        if not self.settings.dry_run:
            u = state.usage
            print(f"  tokens: in={u.tokens_in} out={u.tokens_out} "
                  f"cache_r={u.cache_read} cache_w={u.cache_write}")
            print(f"  coste total: ${u.cost_usd:.4f}")
        print(f"  estado: {state.path}")
        print(f"  proyecto en: {state.root}\n")
