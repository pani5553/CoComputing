#!/usr/bin/env bash
# Launch 3 worker processes in the background for demo purposes.
# Run from the backend/ directory:
#   CC_WORKER_PASSWORD=... bash app/worker/run_workers.sh
#
# Requires: API running at http://localhost:8000
#           Three worker accounts pre-registered in the DB
#           CC_WORKER_PASSWORD set in the environment (no insecure default —
#           see docs/04-arquitectura.md §15.2 / SEC-20)

set -euo pipefail

API="${API_URL:-http://localhost:8000}"
EMAIL_PREFIX="${WORKER_EMAIL_PREFIX:-worker}"
DOMAIN="${WORKER_DOMAIN:-example.com}"
MAX_CHUNKS="${MAX_CHUNKS:-3}"
INTERVAL="${INTERVAL:-5}"

: "${CC_WORKER_PASSWORD:?Debes definir CC_WORKER_PASSWORD antes de ejecutar este script}"
export CC_WORKER_PASSWORD

echo "Lanzando 3 workers contra $API..."

for i in 1 2 3; do
    export CC_WORKER_EMAIL="${EMAIL_PREFIX}${i}@${DOMAIN}"
    python -m app.worker \
        --api "$API" \
        --max-chunks "$MAX_CHUNKS" \
        --interval "$INTERVAL" \
        &
    echo "Worker $i iniciado (PID $!) — email=$CC_WORKER_EMAIL"
done

echo "Todos los workers en background. Usa 'kill $(jobs -p)' para detenerlos."
wait
