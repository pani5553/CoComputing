#!/usr/bin/env bash
# start-local.sh — Levanta Co-Computing en local con Docker Compose.
# Uso: bash deploy/start-local.sh [--prod]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"

# ── Validaciones previas ───────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE no existe."
  echo "Copia deploy/env.example a backend/.env y rellena los valores reales."
  exit 1
fi

# Advertencia si se usa ENVIRONMENT=production en local
if grep -q "^ENVIRONMENT=production" "$ENV_FILE"; then
  echo "AVISO: ENVIRONMENT=production en backend/.env. /docs y /redoc estarán deshabilitados."
fi

# ── Modo producción opcional ───────────────────────────────────────────────────
COMPOSE_ARGS=""
if [ "${1:-}" = "--prod" ]; then
  export ENVIRONMENT=production
  echo "Arrancando en modo producción..."
else
  export ENVIRONMENT=development
  echo "Arrancando en modo desarrollo..."
fi

cd "$ROOT"

# Build + arranque
docker compose build --pull
docker compose up -d

echo ""
echo "Co-Computing levantado:"
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:3000"
if [ "$ENVIRONMENT" = "development" ]; then
  echo "  API docs → http://localhost:8000/docs"
fi
echo ""
echo "Logs: docker compose logs -f"
echo "Stop: docker compose down"
