"""
Rate limiting compartido entre procesos Uvicorn, respaldado por Postgres
(no hay Redis disponible en este proyecto — ver docs/04-arquitectura.md §15.0).
Ventana fija por bucket, atómica vía UPSERT.
"""
import logging
import random
import time
from datetime import datetime, timezone

import psycopg2
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.dependencies import get_current_provider

logger = logging.getLogger(__name__)

_CLEANUP_PROBABILITY = 0.01      # 1% de las llamadas hacen limpieza perezosa
_CLEANUP_MAX_AGE_SECONDS = 3600  # filas de más de 1 hora se consideran basura


def _window_start(window_seconds: int) -> datetime:
    epoch_now = int(time.time())
    bucket_epoch = (epoch_now // window_seconds) * window_seconds
    return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)


def check_rate_limit(bucket: str, limit: int, window_seconds: int) -> None:
    """
    Incrementa el contador de `bucket` para la ventana fija actual (atómico,
    vía UPSERT en Postgres) y lanza HTTPException(429) si supera `limit`.
    Válido entre los N procesos Uvicorn porque el contador vive en la base
    de datos compartida, no en memoria de proceso (ver §15.0).

    Fail-open deliberado ante fallos del pooler de Postgres (EN-MAYOR-02,
    docs/05-review.md 2026-07-09): antes de este ciclo, /auth/login y
    /auth/register no dependían en absoluto de psycopg2 (usan el SDK REST de
    Supabase para todo lo demás). Si la conexión directa al pooler (puerto
    6543) falla o se agota puntualmente, es un problema de infraestructura
    ajeno al REST de Supabase, que puede seguir sano — no debe tumbar login/
    registro con un 500 completo. Se prefiere dejar pasar la petición sin
    contarla (perdiendo, solo para esa petición, la protección de rate limit)
    antes que convertir el rate limiter en un punto único de fallo para la
    autenticación pública. Solo `psycopg2.Error` activa este camino: un bug
    propio (p. ej. parámetros mal formados) no se enmascara, sigue
    propagándose como antes.
    """
    window_start = _window_start(window_seconds)
    try:
        with psycopg2.connect(settings.supabase_db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rate_limit_counters (bucket, window_start, request_count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (bucket, window_start)
                    DO UPDATE SET request_count = rate_limit_counters.request_count + 1
                    RETURNING request_count
                    """,
                    (bucket, window_start),
                )
                (count,) = cur.fetchone()

                if random.random() < _CLEANUP_PROBABILITY:
                    cur.execute(
                        "DELETE FROM rate_limit_counters "
                        "WHERE window_start < now() - make_interval(secs => %s)",
                        (_CLEANUP_MAX_AGE_SECONDS,),
                    )
            conn.commit()
    except psycopg2.Error as exc:
        logger.error(
            "check_rate_limit no pudo conectar/ejecutar contra el pooler de "
            "Postgres (bucket=%s): %s — fail-open: dejando pasar la petición "
            "sin contar (EN-MAYOR-02, docs/05-review.md 2026-07-09).",
            bucket, exc,
        )
        return

    if count > limit:
        logger.warning("Rate limit excedido: bucket=%s count=%d limit=%d", bucket, count, limit)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas peticiones. Inténtalo de nuevo en unos instantes.",
            headers={"Retry-After": str(window_seconds)},
        )


def _client_ip(request: Request) -> str:
    """
    IP real del cliente. Si el backend corre detrás de un proxy reverso,
    requiere `uvicorn --proxy-headers` (ya señalado en el checklist de
    despliegue de docs/06-security.md) para que `request.client.host`
    refleje la IP real y no la del proxy.
    """
    return request.client.host if request.client else "unknown"


def rate_limit_by_ip(scope: str, limit: int, window_seconds: int):
    """Factory de dependencia FastAPI para endpoints públicos, keyed por IP."""
    def _dependency(request: Request) -> None:
        check_rate_limit(f"{scope}:ip:{_client_ip(request)}", limit, window_seconds)
    return _dependency


def rate_limit_by_provider(scope: str, limit: int, window_seconds: int):
    """
    Factory de dependencia FastAPI para endpoints autenticados, keyed por
    provider_id. Sustituye a Depends(get_current_provider) en el endpoint
    (internamente lo llama y devuelve el provider) — no hace falta declarar
    ambas dependencias por separado.
    """
    def _dependency(provider: dict = Depends(get_current_provider)) -> dict:
        check_rate_limit(f"{scope}:provider:{provider['id']}", limit, window_seconds)
        return provider
    return _dependency
