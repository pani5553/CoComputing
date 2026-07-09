"""
Aislamiento de proceso para el cómputo de un chunk (primer paso — ver
docs/04-arquitectura.md §15.3). Ejecuta plugin.process(payload) en un
subproceso separado con límites de CPU/memoria y timeout duro, para que
un payload patológico no pueda colgar ni tumbar el proceso worker principal.

NO es sandboxing completo: no hay aislamiento de red, filesystem ni
namespaces de SO. Ver §15.3.5 de docs/04-arquitectura.md para el alcance
que queda deliberadamente fuera de este ciclo (contenedores con
seccomp/AppArmor, sin acceso a red saliente, filesystem de solo lectura).
Lo que este módulo SÍ resuelve: un chunk que se cuelga, agota memoria o
crashea ya no se lleva por delante el proceso worker completo (con todo
el trabajo en curso de otros chunks), solo el subproceso aislado de ese
chunk. Además (SEC-37, docs/06-security.md 2026-07-09), el subproceso
recorta su propio entorno heredado a una allowlist mínima antes de
ejecutar el plugin, para que CC_WORKER_EMAIL/CC_WORKER_PASSWORD y otros
secretos del worker padre no queden accesibles a un plugin comprometido.
"""
import logging
import multiprocessing as mp
import os
import sys
import time
from typing import Any

logger = logging.getLogger("worker")

CHUNK_TIMEOUT_SECONDS = 30      # timeout duro de pared por chunk
CHUNK_CPU_LIMIT_SECONDS = 25    # límite de tiempo de CPU (RLIMIT_CPU), algo por debajo del timeout de pared
CHUNK_MEMORY_LIMIT_MB = 512     # límite de memoria virtual (RLIMIT_AS) del subproceso

# Variables mínimas que el subproceso necesita para seguir funcionando
# (localizar el intérprete/binarios, temporales, locale). Todo lo demás —
# en particular CC_WORKER_EMAIL/CC_WORKER_PASSWORD y cualquier otro secreto
# del proceso worker padre (SUPABASE_*, JWT_SECRET_KEY, etc.) — se descarta
# antes de ejecutar cualquier código de plugin (SEC-37, docs/06-security.md
# 2026-07-09): el subproceso `spawn` no necesita ninguna de esas variables,
# porque la autenticación ya ocurrió en login() antes de que exista ningún
# chunk que procesar.
_CHILD_ENV_ALLOWLIST = {
    "PATH", "LANG", "LC_ALL",
    # Solo relevantes en Windows (entorno de desarrollo local — el
    # despliegue real en deploy/backend.Dockerfile es Linux); se conservan
    # para que el propio intérprete y librerías nativas (p. ej. polars)
    # sigan funcionando tras el recorte.
    "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "PATHEXT", "COMSPEC",
    "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
}


def _scrub_child_environment() -> None:
    """
    Recorta os.environ del subproceso a una allowlist mínima.

    `multiprocessing` con el contexto `spawn` (usado en `run_chunk_sandboxed`)
    no expone un parámetro `env=` como `subprocess.Popen` — el hijo ya hereda
    el entorno completo del padre en el momento del spawn. Esta función se
    ejecuta como la PRIMERA acción de `_child_entrypoint`, antes de importar
    o ejecutar ningún código de plugin, para que cuando `plugin.process()`
    corra, `os.environ` ya no contenga ningún secreto del worker padre.
    """
    for key in list(os.environ.keys()):
        if key.upper() not in _CHILD_ENV_ALLOWLIST:
            del os.environ[key]


def _child_entrypoint(job_type: str, payload: dict, result_queue: "mp.Queue") -> None:
    """
    Punto de entrada del subproceso hijo. Recorta el entorno heredado (ver
    SEC-37), aplica límites de recursos (si el SO los soporta) y ejecuta el
    plugin.
    """
    _scrub_child_environment()

    if sys.platform != "win32":
        # El módulo `resource` es POSIX-only. En Windows (solo relevante para
        # desarrollo local, no para el despliegue en `deploy/backend.Dockerfile`,
        # que es Linux) se omiten los límites de CPU/memoria y solo queda el
        # timeout de pared (ver la nota de portabilidad más abajo).
        import resource

        resource.setrlimit(
            resource.RLIMIT_CPU, (CHUNK_CPU_LIMIT_SECONDS, CHUNK_CPU_LIMIT_SECONDS)
        )
        mem_bytes = CHUNK_MEMORY_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    from app.worker.plugins import get_plugin  # import diferido: solo necesario en el hijo

    try:
        plugin = get_plugin(job_type)
        if plugin is None:
            result_queue.put({"ok": False, "error": f"unsupported job_type: {job_type}"})
            return
        result = plugin.process(payload)
        result_queue.put({"ok": True, "result": result})
    except MemoryError:
        result_queue.put({"ok": False, "error": "chunk excedió el límite de memoria del subproceso"})
    except Exception as exc:
        result_queue.put({"ok": False, "error": str(exc)})


def run_chunk_sandboxed(job_type: str, payload: dict[str, Any]) -> tuple[dict, int]:
    """
    Ejecuta el procesamiento de un chunk en un subproceso aislado.
    Devuelve (result_dict, duration_ms) — misma forma que la función
    `process_chunk` de `worker/main.py`, a la que sustituye internamente.

    - Timeout duro de pared: CHUNK_TIMEOUT_SECONDS. Si se excede, el
      subproceso se termina (SIGTERM y, si no responde, SIGKILL) y se
      devuelve un error — el proceso worker principal sobrevive siempre.
    - Límites de CPU/memoria (RLIMIT_CPU/RLIMIT_AS): solo aplican en POSIX
      (ver `_child_entrypoint`); en Windows solo queda el timeout de pared.
    """
    ctx = mp.get_context("spawn")  # spawn (no fork): el hijo no hereda estado del padre
    result_queue: "mp.Queue" = ctx.Queue()
    start = time.monotonic()

    proc = ctx.Process(target=_child_entrypoint, args=(job_type, payload, result_queue))
    proc.start()
    proc.join(timeout=CHUNK_TIMEOUT_SECONDS)
    elapsed_ms = max(1, int((time.monotonic() - start) * 1000))

    if proc.is_alive():
        logger.error("Chunk excedió el timeout de %ds — terminando subproceso", CHUNK_TIMEOUT_SECONDS)
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return {"error": f"chunk processing timed out after {CHUNK_TIMEOUT_SECONDS}s"}, elapsed_ms

    if proc.exitcode != 0:
        # Terminado por señal (OOM/RLIMIT → SIGKILL/SIGSEGV) o excepción no capturada en el hijo.
        logger.error("Subproceso del chunk terminó con código anómalo: %s", proc.exitcode)
        return {"error": f"chunk process exited abnormally (code={proc.exitcode})"}, elapsed_ms

    try:
        outcome = result_queue.get_nowait()
    except Exception:
        return {"error": "chunk process produced no result"}, elapsed_ms

    if not outcome.get("ok"):
        return {"error": outcome.get("error", "unknown error")}, elapsed_ms
    return outcome["result"], elapsed_ms
