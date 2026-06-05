"""
Agent — ejecuta UN rol del organigrama.

Toma su RoleSpec, construye el system prompt (identidad + reglas globales +
scope), inyecta el estado del proyecto y el encargo, y corre el tool-use loop
con un ToolExecutor que tiene el FileGate de ESE rol.
"""
from __future__ import annotations

from pathlib import Path

from .filegate import FileGate
from .llm import LLMClient, RunResult
from .state import ProjectState
from .tools import ToolExecutor, build_tools


GLOBAL_RULES = """\
REGLAS GLOBALES DE LA FACTORIA (validas para todos los roles):
1. Haces SOLO tu trabajo. No invadas el area de otros roles. Si algo no es tuyo,
   dejalo indicado en el handoff para quien corresponda.
2. SCOPE DE ESCRITURA: solo puedes escribir en las rutas de tu scope (abajo).
   Cualquier intento fuera de scope sera RECHAZADO por el sistema.
3. Puedes LEER cualquier fichero del proyecto para entender el trabajo previo.
   Empieza leyendo lo que han dejado los agentes anteriores.
4. Produce trabajo de calidad de PRODUCCION, no placeholders ni "TODO".
   Codigo real, completo y coherente con lo que ya existe.
5. Cuando termines, llama finish() con un resumen y un handoff claro para el
   siguiente rol. No termines sin haber producido tus artefactos.
"""


class Agent:
    def __init__(self, spec, settings, workspace_root: Path, state: ProjectState, llm: LLMClient):
        self.spec = spec
        self.settings = settings
        self.workspace_root = workspace_root
        self.state = state
        self.llm = llm

    def _system(self) -> str:
        scope = "\n".join(f"  - {p}" for p in self.spec.allowed_write) or "  (no escribes ficheros, solo lees y documentas)"
        return (
            f"{self.spec.system}\n\n"
            f"{GLOBAL_RULES}\n"
            f"TU SCOPE DE ESCRITURA ({self.spec.title}):\n{scope}\n"
        )

    def _user(self) -> str:
        return (
            f"# ENCARGO DEL CLIENTE\n{self.state.brief}\n\n"
            f"{self.state.context_digest()}\n\n"
            f"---\nAhora ejecuta tu rol de **{self.spec.title}**. "
            f"Lee primero el trabajo previo, luego produce tus artefactos dentro de tu scope, "
            f"y termina con finish()."
        )

    @property
    def model(self) -> str:
        if self.spec.model:
            return self.spec.model
        return self.settings.model_director if self.spec.director else self.settings.model_default

    def run(self) -> RunResult:
        gate = FileGate(self.workspace_root, self.spec.allowed_write)
        executor = ToolExecutor(
            workspace_root=self.workspace_root,
            gate=gate,
            can_run=self.spec.can_run,
        )
        tools = build_tools(can_write=self.spec.can_write, can_run=self.spec.can_run)
        return self.llm.run(
            system=self._system(),
            user=self._user(),
            tools=tools,
            executor=executor,
            model=self.model,
            max_iterations=self.settings.max_iterations,
            dry_artifact=self.spec.dry_artifact,
        )
