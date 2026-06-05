"""
Tools que los agentes pueden invocar. El conjunto disponible para cada agente
depende de su RoleSpec (can_write, can_run). La lectura la tienen todos.

Tools:
  read_file(path)            Lee un fichero del workspace (cualquiera).
  list_dir(path=".")         Lista el contenido de una carpeta.
  write_file(path, content)  Crea/sobrescribe un fichero. PASA POR FILEGATE.
  run_command(command)       Ejecuta un comando en el workspace. Solo can_run.
  finish(summary, handoff)   Declara el trabajo terminado y traspasa al siguiente.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .filegate import FileGate, ScopeViolation


# ── Schemas (formato Anthropic tool-use) ──────────────────────────────────────

_READ = {
    "name": "read_file",
    "description": "Lee el contenido de un fichero del proyecto. Puedes leer cualquier fichero del workspace para ver el trabajo de otros agentes.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Ruta relativa al workspace"}},
        "required": ["path"],
    },
}

_LIST = {
    "name": "list_dir",
    "description": "Lista ficheros y carpetas. Util para explorar la estructura del proyecto.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Ruta relativa (por defecto la raiz del proyecto)"}},
    },
}

_WRITE = {
    "name": "write_file",
    "description": (
        "Crea o sobrescribe un fichero. SOLO puedes escribir dentro de tu scope "
        "asignado; si intentas escribir fuera, la operacion sera rechazada."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta relativa al workspace"},
            "content": {"type": "string", "description": "Contenido completo del fichero"},
        },
        "required": ["path", "content"],
    },
}

_RUN = {
    "name": "run_command",
    "description": (
        "Ejecuta un comando de shell en la raiz del workspace (ej. 'pytest', "
        "'python -m py_compile ...'). Solo disponible para roles autorizados."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}

_FINISH = {
    "name": "finish",
    "description": (
        "Llama a esto cuando hayas COMPLETADO tu trabajo. Resume lo que hiciste y "
        "deja instrucciones claras para el siguiente agente de la cadena."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Resumen de lo que has hecho"},
            "handoff": {"type": "string", "description": "Instrucciones/contexto para el siguiente agente"},
        },
        "required": ["summary", "handoff"],
    },
}


def build_tools(can_write: bool, can_run: bool) -> list[dict]:
    tools = [_READ, _LIST]
    if can_write:
        tools.append(_WRITE)
    if can_run:
        tools.append(_RUN)
    tools.append(_FINISH)
    return tools


# ── Ejecutor ──────────────────────────────────────────────────────────────────

@dataclass
class FinishSignal:
    summary: str
    handoff: str


@dataclass
class ToolExecutor:
    workspace_root: Path
    gate: FileGate
    can_run: bool
    artifacts: list[str] = field(default_factory=list)
    finished: Optional[FinishSignal] = None
    run_timeout: int = 180

    def execute(self, name: str, args: dict) -> str:
        try:
            if name == "read_file":
                return self._read(args["path"])
            if name == "list_dir":
                return self._list(args.get("path", "."))
            if name == "write_file":
                return self._write(args["path"], args["content"])
            if name == "run_command":
                return self._run(args["command"])
            if name == "finish":
                self.finished = FinishSignal(args.get("summary", ""), args.get("handoff", ""))
                return "OK. Trabajo marcado como terminado."
            return f"ERROR: tool desconocida '{name}'"
        except ScopeViolation as exc:
            return f"ERROR: {exc}"
        except Exception as exc:
            return f"ERROR ejecutando {name}: {exc}"

    # ── implementaciones ──────────────────────────────────────────────────────
    def _read(self, path: str) -> str:
        p = self.gate.resolve(path)
        if not p.exists():
            return f"ERROR: el fichero '{path}' no existe."
        if p.is_dir():
            return f"ERROR: '{path}' es una carpeta. Usa list_dir."
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > 60_000:
            text = text[:60_000] + "\n...[truncado]"
        return text

    def _list(self, path: str) -> str:
        p = self.gate.resolve(path)
        if not p.exists():
            return f"(vacio: '{path}' no existe todavia)"
        if p.is_file():
            return self.gate.rel(path)
        entries = []
        for child in sorted(p.iterdir()):
            rel = child.relative_to(self.gate.root).as_posix()
            entries.append(rel + ("/" if child.is_dir() else ""))
        return "\n".join(entries) if entries else "(carpeta vacia)"

    def _write(self, path: str, content: str) -> str:
        self.gate.check_write(path)  # lanza ScopeViolation si fuera de scope
        p = self.gate.resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        rel = self.gate.rel(path)
        if rel not in self.artifacts:
            self.artifacts.append(rel)
        return f"OK. Escrito '{rel}' ({len(content)} chars)."

    def _run(self, command: str) -> str:
        if not self.can_run:
            return "ERROR: tu rol no tiene permiso para ejecutar comandos."
        try:
            proc = subprocess.run(
                command, shell=True, cwd=str(self.workspace_root),
                capture_output=True, text=True, timeout=self.run_timeout,
            )
            out = (proc.stdout or "")[-8000:]
            err = (proc.stderr or "")[-4000:]
            return f"exit_code={proc.returncode}\n--- stdout ---\n{out}\n--- stderr ---\n{err}"
        except subprocess.TimeoutExpired:
            return f"ERROR: el comando supero el timeout de {self.run_timeout}s."
