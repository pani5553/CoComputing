# ── Stage 1: dependencies ─────────────────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /build

# Dependencias de sistema para psycopg2-binary y cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: production ───────────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Usuario sin privilegios: no correr como root
RUN adduser --system --no-create-home --group appuser

WORKDIR /app

# Copiar paquetes instalados
COPY --from=deps /install /usr/local

# Copiar código de la aplicación
COPY backend/app/ ./app/

# Asignar propiedad
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
