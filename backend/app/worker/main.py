"""
Co-Computing Worker — standalone process that polls the API and processes chunks.

Usage (recommended — credentials via environment, never visible in `ps aux`
or shell history, see docs/04-arquitectura.md §15.2):
    export CC_WORKER_EMAIL=worker@example.com
    export CC_WORKER_PASSWORD=secret123
    python -m app.worker --api http://localhost:8000 [--max-chunks 3] [--interval 5]

Usage (deprecated — kept for backwards compatibility, emits a warning):
    python -m app.worker \
        --api http://localhost:8000 \
        --email worker@example.com \
        --password secret123 \
        [--max-chunks 3] \
        [--interval 5]

SECURITY NOTE: chunk processing runs inside a sandboxed subprocess with a
hard timeout and CPU/memory limits (see app/worker/sandbox.py) — this is a
first step, not full container/seccomp isolation. Do NOT run this worker
against untrusted API endpoints in production without adding proper
isolation (Docker seccomp, AppArmor, etc.) if a future plugin invokes
external binaries.
"""
import argparse
import logging
import os
import sys
import time
from typing import Any

import httpx

from app.worker.sandbox import run_chunk_sandboxed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] worker: %(message)s",
)
logger = logging.getLogger("worker")


def login(api: str, email: str, password: str) -> str:
    """Authenticate against POST /auth/login and return the JWT."""
    response = httpx.post(
        f"{api}/auth/login",
        json={"email": email, "password": password},
        timeout=15.0,
    )
    if response.status_code != 200:
        logger.error("Login fallido (%s): %s", response.status_code, response.text)
        sys.exit(1)
    token = response.json().get("access_token")
    if not token:
        logger.error("No se recibió access_token en la respuesta de login")
        sys.exit(1)
    logger.info("Login exitoso como %s", email)
    return token


def claim_chunks(api: str, headers: dict, max_chunks: int) -> list[dict]:
    """POST /work/claim and return the list of chunks (may be empty)."""
    response = httpx.post(
        f"{api}/work/claim",
        json={"max_chunks": max_chunks},
        headers=headers,
        timeout=15.0,
    )
    if response.status_code == 401:
        # Token expired — signal caller to re-login
        raise PermissionError("Token expirado")
    if response.status_code != 200:
        logger.warning("Claim fallido (%s): %s", response.status_code, response.text)
        return []
    return response.json().get("chunks", [])


def submit_result(api: str, headers: dict, chunk_id: str, result: dict, duration_ms: int) -> None:
    """POST /work/{chunk_id}/submit with the computed result."""
    response = httpx.post(
        f"{api}/work/{chunk_id}/submit",
        json={"result": result, "duration_ms": duration_ms},
        headers=headers,
        timeout=15.0,
    )
    if response.status_code == 200:
        data = response.json()
        logger.info(
            "Chunk %s enviado → status=%s | %s",
            chunk_id[:8],
            data.get("status"),
            data.get("message"),
        )
    else:
        logger.warning(
            "Submit fallido para chunk %s (%s): %s",
            chunk_id[:8],
            response.status_code,
            response.text,
        )


def process_chunk(chunk: dict) -> tuple[dict, int]:
    """
    Dispatch the chunk payload to the appropriate plugin, running it inside
    an isolated subprocess (see app/worker/sandbox.py) so that a pathological
    payload (hang, runaway memory/CPU) cannot take down the worker process
    itself. Returns (result_dict, duration_ms).
    """
    job_type = chunk.get("job_type", "data-processing")
    payload = chunk.get("payload", {})
    return run_chunk_sandboxed(job_type, payload)


def run_worker(api: str, email: str, password: str, max_chunks: int, interval: int) -> None:
    """Main polling loop."""
    token = login(api, email, password)
    headers = {"Authorization": f"Bearer {token}"}
    backoff = interval

    logger.info("Worker iniciado. Polling cada %ds, max_chunks=%d", interval, max_chunks)

    while True:
        try:
            chunks = claim_chunks(api, headers, max_chunks)
        except PermissionError:
            logger.info("Renovando token...")
            token = login(api, email, password)
            headers = {"Authorization": f"Bearer {token}"}
            chunks = []
        except Exception as exc:
            logger.warning("Error en claim: %s — reintentando en %ds", exc, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if not chunks:
            logger.debug("Sin chunks disponibles. Esperando %ds...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        # Reset backoff when work is found
        backoff = interval

        for chunk in chunks:
            chunk_id = str(chunk.get("chunk_id", ""))
            logger.info(
                "Procesando chunk %s (job=%s, idx=%s)",
                chunk_id[:8],
                str(chunk.get("job_id", ""))[:8],
                chunk.get("chunk_index"),
            )
            result, duration_ms = process_chunk(chunk)
            submit_result(api, headers, chunk_id, result, duration_ms)


def resolve_worker_credentials(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> tuple[str, str]:
    """
    Resuelve email y password del worker.
    Prioridad: variables de entorno CC_WORKER_EMAIL / CC_WORKER_PASSWORD
    (recomendado) sobre los argumentos --email/--password (deprecados,
    visibles en `ps aux` y en el historial de shell — SEC-20).

    Lanza parser.error(...) (SystemExit) si, tras aplicar la precedencia,
    falta el email o el password.
    """
    email = os.environ.get("CC_WORKER_EMAIL") or args.email
    password = os.environ.get("CC_WORKER_PASSWORD") or args.password

    if args.password and not os.environ.get("CC_WORKER_PASSWORD"):
        logger.warning(
            "DEPRECADO: --password expone la contraseña en `ps aux` y el historial de "
            "shell (SEC-20). Usa la variable de entorno CC_WORKER_PASSWORD. "
            "El argumento --password se eliminará en una futura versión."
        )

    if args.email and not os.environ.get("CC_WORKER_EMAIL"):
        logger.warning(
            "DEPRECADO: --email debería pasarse vía CC_WORKER_EMAIL. "
            "El argumento --email se conservará, pero se recomienda migrar."
        )

    if not email or not password:
        parser.error(
            "Credenciales requeridas: define CC_WORKER_EMAIL y CC_WORKER_PASSWORD "
            "(recomendado) o usa --email/--password (deprecado)."
        )
    return email, password


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Co-Computing Worker — procesa chunks distribuidos"
    )
    parser.add_argument("--api", default="http://localhost:8000", help="URL base de la API")
    parser.add_argument(
        "--email",
        default=None,
        help="[DEPRECADO] Email del proveedor/worker. Usa CC_WORKER_EMAIL en su lugar.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="[DEPRECADO] Contraseña del proveedor/worker. Usa CC_WORKER_PASSWORD en su lugar.",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=3,
        dest="max_chunks",
        help="Máximo de chunks a reclamar por ciclo (1-10, default 3)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Segundos entre ciclos de polling cuando no hay trabajo (default 5)",
    )
    args = parser.parse_args()

    email, password = resolve_worker_credentials(args, parser)

    run_worker(
        api=args.api,
        email=email,
        password=password,
        max_chunks=args.max_chunks,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()
