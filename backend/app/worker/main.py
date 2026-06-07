"""
Co-Computing Worker — standalone process that polls the API and processes chunks.

Usage:
    python -m app.worker \
        --api http://localhost:8000 \
        --email worker@example.com \
        --password secret123 \
        [--max-chunks 3] \
        [--interval 5]

SECURITY NOTE: The worker executes payloads from the server without sandboxing.
Payloads are restricted to tabular data (lists of lists); no eval/exec is used.
Do NOT run this worker against untrusted API endpoints in production without
adding proper isolation (Docker seccomp, AppArmor, etc.).
"""
import argparse
import logging
import sys
import time
from typing import Any

import httpx

from app.worker.plugins import get_plugin

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
    Dispatch the chunk payload to the appropriate plugin.
    Returns (result_dict, duration_ms).
    """
    job_type = chunk.get("job_type", "data-processing")
    payload = chunk.get("payload", {})

    plugin = get_plugin(job_type)
    if plugin is None:
        logger.error("Tipo de job no soportado por este worker: %s", job_type)
        return {"error": f"unsupported job_type: {job_type}"}, 1

    start = time.monotonic()
    try:
        result = plugin.process(payload)
    except Exception as exc:
        logger.error("Error procesando chunk: %s", exc, exc_info=True)
        result = {"error": str(exc)}
    elapsed_ms = max(1, int((time.monotonic() - start) * 1000))
    return result, elapsed_ms


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Co-Computing Worker — procesa chunks distribuidos"
    )
    parser.add_argument("--api", default="http://localhost:8000", help="URL base de la API")
    parser.add_argument("--email", required=True, help="Email del proveedor/worker")
    parser.add_argument("--password", required=True, help="Contraseña del proveedor/worker")
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

    run_worker(
        api=args.api,
        email=args.email,
        password=args.password,
        max_chunks=args.max_chunks,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()
