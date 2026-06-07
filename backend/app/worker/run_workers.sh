#!/usr/bin/env bash
# Launch 3 worker processes in the background for demo purposes.
# Run from the backend/ directory:
#   bash app/worker/run_workers.sh
#
# Requires: API running at http://localhost:8000
#           Three worker accounts pre-registered in the DB

set -euo pipefail

API="${API_URL:-http://localhost:8000}"
EMAIL_PREFIX="${WORKER_EMAIL_PREFIX:-worker}"
DOMAIN="${WORKER_DOMAIN:-example.com}"
PASSWORD="${WORKER_PASSWORD:-password123}"
MAX_CHUNKS="${MAX_CHUNKS:-3}"
INTERVAL="${INTERVAL:-5}"

echo "Lanzando 3 workers contra $API..."

for i in 1 2 3; do
    EMAIL="${EMAIL_PREFIX}${i}@${DOMAIN}"
    python -m app.worker \
        --api "$API" \
        --email "$EMAIL" \
        --password "$PASSWORD" \
        --max-chunks "$MAX_CHUNKS" \
        --interval "$INTERVAL" \
        &
    echo "Worker $i iniciado (PID $!) — email=$EMAIL"
done

echo "Todos los workers en background. Usa 'kill $(jobs -p)' para detenerlos."
wait
