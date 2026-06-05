# Co-Computing — Backend

FastAPI + Uvicorn REST API para la plataforma de computación distribuida Co-Computing.

## Requisitos previos

- Python 3.12+
- Proyecto en [Supabase Cloud](https://supabase.com) con el schema aplicado
- Clave `service_role` de Supabase (no la `anon`)

## Arranque en desarrollo (cold start < 5 min)

### 1. Clonar y preparar entorno

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con los valores reales:
#   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL
#   JWT_SECRET_KEY (min. 32 chars — generar con: openssl rand -hex 32)
```

### 3. Aplicar el schema en Supabase

Ejecutar en el SQL Editor de Supabase (en este orden):

1. `migrations/001_schema.sql` — crea las 5 tablas, triggers e índices
2. `app/db/rls_policies.sql` — activa RLS y aplica políticas

### 4. Insertar datos de seed (tareas de ejemplo)

```bash
python scripts/seed.py
```

Esto inserta 18 tareas representativas de forma idempotente
(`INSERT ... ON CONFLICT DO NOTHING`).

### 5. Arrancar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

La API estará disponible en `http://localhost:8000`.
Documentación interactiva: `http://localhost:8000/docs` (solo en desarrollo).

---

## Ejecutar tests

```bash
pytest --cov=app --cov-report=html
```

Cobertura mínima requerida: **80%**.

```bash
# Lint y formato
ruff check .
ruff format .
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SUPABASE_URL` | URL del proyecto Supabase | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave service_role (bypasea RLS) | `eyJ...` |
| `SUPABASE_DB_URL` | Cadena de conexión psycopg2 | `postgresql://postgres:pwd@...` |
| `JWT_SECRET_KEY` | Secreto JWT (min. 32 chars) | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | Algoritmo JWT | `HS256` |
| `JWT_EXPIRE_DAYS` | Expiración del token en días | `7` |
| `FRONTEND_URL` | URL del frontend para CORS | `http://localhost:5173` |
| `ENVIRONMENT` | `development` o `production` | `development` |

En `production`, los endpoints `/docs` y `/redoc` quedan deshabilitados
y el nivel de log sube a `WARNING`.

---

## Estructura del proyecto

```
backend/
  app/
    main.py              # FastAPI app, CORS, middleware, routers
    core/
      config.py          # Settings con pydantic-settings
      security.py        # JWT, bcrypt
      dependencies.py    # get_current_provider (Depends)
    db/
      client.py          # Singleton Supabase client
      queries/           # Modulos de queries por dominio
      rls_policies.sql   # Politicas RLS
    models/              # Pydantic v2 schemas
    routers/             # auth, tasks, wallet, profile
    services/            # logica de negocio
    seed/
      tasks_seed.sql     # 18 tareas de ejemplo
      seed.py            # Script de seed
  scripts/
    seed.py              # Punto de entrada para el seed
  tests/                 # pytest + httpx
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  .env.example
```

---

## Endpoints implementados

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Registro de proveedor + creacion de cartera |
| POST | `/auth/login` | No | Login, devuelve JWT (7 dias) |
| GET | `/auth/me` | Si | Perfil completo del proveedor autenticado |
| GET | `/tasks/` | Si | Listado de tareas con filtros (difficulty, hardware, type, min_reward) |
| GET | `/tasks/my/history` | Si | Historial de asignaciones del proveedor |
| GET | `/tasks/{task_id}` | Si | Detalle de tarea + active_assignment |
| POST | `/tasks/{task_id}/accept` | Si | Acepta tarea (decremento atomico de slots) |
| POST | `/tasks/{task_id}/start` | Si | Inicia procesamiento |
| POST | `/tasks/{task_id}/complete` | Si | Completa tarea, acredita recompensa |
| POST | `/tasks/{task_id}/fail` | Si | Reporta fallo, penaliza trust score |
| GET | `/tasks/assignments/{id}/progress` | Si | Progreso simulado (polling) |
| GET | `/wallet/` | Si | Saldos de cartera |
| GET | `/wallet/transactions` | Si | Historial de transacciones paginado |
| POST | `/wallet/withdraw` | Si | Solicitar retiro de fondos |
| GET | `/profile/stats` | Si | Perfil + Trust Score desglosado + rank info |
| PUT | `/profile/hardware` | Si | Actualizar especificaciones de hardware |
| PATCH | `/profile/online` | Si | Toggle estado online |
| PATCH | `/profile/name` | Si | Actualizar nombre completo |
| GET | `/health` | No | Health check (solo en development) |
