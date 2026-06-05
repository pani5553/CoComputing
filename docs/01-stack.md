# Co-Computing — Stack Técnico y Arquitectura

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** CTO
**Referencia:** `docs/00-vision.md`, `briefs/co-computing.md`

---

## 1. Resumen Ejecutivo del Stack

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Frontend | React + Vite | React 18.3, Vite 5.4 |
| Estilos | Tailwind CSS | 3.4 |
| Estado global | Zustand | 4.5 |
| HTTP cliente | Axios | 1.7 |
| Backend | FastAPI + Uvicorn | FastAPI 0.115, Uvicorn 0.32 |
| ORM / DB client | Supabase Python SDK + psycopg2 | supabase 2.x, psycopg2-binary 2.9 |
| Base de datos | Supabase (PostgreSQL 15) | Hosted (cloud) |
| Autenticación | JWT HS256, expiración 7 días | python-jose 3.3 |
| Hash de passwords | bcrypt via passlib | passlib[bcrypt] 1.7 |
| Tests backend | pytest + httpx | pytest 8.x, httpx 0.27 |
| Tests frontend | Vitest + Testing Library | Vitest 2.x, @testing-library/react 16.x |
| Validación API | Pydantic v2 | 2.9 |
| Linter / Formatter (PY) | Ruff | 0.6 |
| Linter / Formatter (JS) | ESLint 9 + Prettier 3 | — |

---

## 2. Justificación de Decisiones Clave

### 2.1 Stack obligatorio (respetado integramente)
El brief especifica React + Vite, FastAPI + Uvicorn y Supabase con JWT HS256. Estas elecciones son razonables y coherentes con el tipo de producto: SPA de alta interactividad, API Python de ciclo rápido de desarrollo y base de datos gestionada con Row Level Security nativa.

### 2.2 Tailwind CSS en lugar de una libreria de componentes completa
El proveedor de cómputo necesita una UI limpia, en español y con estados muy explícitos (cargando, error, éxito). Tailwind permite construir esa UI con precisión sin importar un sistema de diseño ajeno que habria que sobreescribir. Se añaden componentes Headless UI (1.x) solo para primitivas accesibles (modales, dropdowns) sin opinion visual.

### 2.3 Zustand en lugar de Redux Toolkit
La superficie de estado global del MVP es acotada: usuario autenticado, tarea en progreso, balance de cartera. Redux introduce boilerplate que no se justifica. Zustand ofrece un store tipado con Immer opcional y persistencia via middleware con una API minima.

### 2.4 Monorepo con separacion de directorios (no Turborepo)
El proyecto es pequeño (un equipo, un producto, un deployment). Un monorepo simple con `/frontend` y `/backend` en la misma raiz proporciona todos los beneficios (un solo `git clone`, variables de entorno compartidas en `.env.example`, CI unificado) sin la complejidad operativa de Turborepo o Nx que no aportaria valor en este estadio.

### 2.5 Supabase Python SDK + consultas directas via SQL crudo
El SDK de Supabase para Python simplifica las operaciones CRUD y la integración de RLS. Para queries complejas (historial con joins, estadísticas del dashboard) se usara SQL crudo via `supabase.rpc()` o psycopg2 directo con conexion pooled desde la Connection String de Supabase. No se introduce SQLAlchemy para evitar una capa de abstraccion extra sin valor añadido en este MVP.

### 2.6 JWT gestionado en el backend propio, no con Supabase Auth
El brief especifica JWT HS256 con expiración de 7 días. Supabase Auth utiliza RS256 y gestiona los tokens en su propio servicio. Se implementa la autenticación completa en FastAPI (registro, login, validacion de token) usando `python-jose` y `passlib[bcrypt]`. Supabase se usa exclusivamente como base de datos PostgreSQL. La clave secreta JWT vive en variable de entorno `JWT_SECRET_KEY`.

### 2.7 Simulación de progreso de tareas
El procesamiento real de cómputo está fuera del alcance del MVP. La simulacion se implementa como sigue:

- Al llamar `POST /tasks/{id}/start`, el backend crea la asignacion en estado `procesando` y devuelve un `processing_token` (UUID v4) y el número de etapas simuladas (entre 4 y 6 según la duracion estimada de la tarea).
- El frontend llama a `GET /tasks/assignments/{assignment_id}/progress` cada 3 segundos. El backend calcula el progreso en función del tiempo transcurrido desde `started_at` y la duracion estimada de la tarea: `progreso = min((now - started_at) / duracion_estimada * 100, 99)`.
- El progreso nunca llega a 100 automaticamente: el proveedor debe presionar "Completar" para cerrar el ciclo. Esto refleja la semantica real (el proveedor confirma que el trabajo esta listo) y evita completados automaticos no supervisados.
- Las etapas tienen nombres descriptivos definidos en la tarea (`stages: ["Preparando entorno", "Descargando dataset", "Procesando", "Validando resultados", "Empaquetando salida"]`) y se derivan del índice de progreso para dar sensacion de avance real.
- El Trust Score se recalcula en el backend en cada transicion de estado de la asignacion.

### 2.8 Seed de tareas (sin panel cliente en el MVP)
Las tareas disponibles en la plataforma son datos de seed insertados directamente en la tabla `tasks` de Supabase. El mecanismo es:

- Fichero `backend/app/seed/tasks_seed.sql`: contiene 15-20 tareas representativas con variedad de tipo (renderizado 3D, entrenamiento ML, transcodificacion de video, analisis de datos, simulacion fisica), dificultad, hardware requerido y recompensa.
- Script `backend/scripts/seed.py`: ejecuta el SQL contra la base de datos usando las variables de entorno del entorno activo. Idempotente (usa `INSERT ... ON CONFLICT DO NOTHING`).
- Instruccion en el README: `python backend/scripts/seed.py` como paso obligatorio del setup local.
- En produccion, el seed se ejecuta manualmente una sola vez desde el entorno de CI o la maquina del desarrollador apuntando al proyecto Supabase de produccion.

---

## 3. Arquitectura Macro

```
┌─────────────────────────────────────────────────────────┐
│                    NAVEGADOR                            │
│                                                         │
│   React SPA (Vite)                                      │
│   ├── /auth         (login, registro)                   │
│   ├── /dashboard    (metricas, tareas recientes)        │
│   ├── /tasks        (listado con filtros)               │
│   ├── /tasks/:id    (detalle y aceptacion)              │
│   ├── /processing/:assignmentId  (progreso por etapas)  │
│   ├── /wallet       (cartera y retiros)                 │
│   └── /profile      (perfil, hardware, trust score)    │
│                                                         │
│   Zustand Store: { user, token, currentAssignment }     │
│   Axios instance: baseURL = VITE_API_URL, JWT header    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS REST JSON
                     │ Authorization: Bearer <jwt>
┌────────────────────▼────────────────────────────────────┐
│                 FastAPI + Uvicorn                        │
│                                                         │
│   app/                                                  │
│   ├── routers/                                          │
│   │   ├── auth.py       (register, login, me)           │
│   │   ├── tasks.py      (list, detail, lifecycle)       │
│   │   ├── wallet.py     (balance, transactions, withdraw)│
│   │   └── profile.py   (stats, hardware, online toggle) │
│   ├── models/           (Pydantic v2 schemas)           │
│   ├── services/         (business logic, trust score)   │
│   ├── db/               (supabase client, queries)      │
│   ├── core/             (config, security, deps)        │
│   └── seed/             (SQL + script de seed)          │
│                                                         │
│   CORS: Allow-Origin = FRONTEND_URL (env var)           │
│   JWT: HS256, SECRET_KEY desde env, exp 7d              │
└────────────────────┬────────────────────────────────────┘
                     │ Supabase Python SDK / psycopg2
                     │ Connection String (pooled, port 6543)
┌────────────────────▼────────────────────────────────────┐
│              Supabase (PostgreSQL 15)                   │
│                                                         │
│   Tablas: providers, tasks, task_assignments,           │
│            wallets, transactions                        │
│                                                         │
│   Row Level Security activado en todas las tablas.      │
│   Las politicas RLS garantizan que cada proveedor       │
│   solo accede a sus propios registros.                  │
│   La service_role key (backend) bypasea RLS             │
│   de forma controlada para operaciones administrativas. │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Estructura de Carpetas del Repositorio

```
co-computing/
├── .env.example                  # Variables requeridas documentadas, sin valores reales
├── .gitignore
├── README.md
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── eslint.config.js
│   ├── .prettierrc
│   ├── package.json
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   └── src/
│       ├── main.tsx              # Entry point, BrowserRouter, QueryClientProvider
│       ├── App.tsx               # Rutas con React Router v6, ProtectedRoute
│       │
│       ├── api/
│       │   ├── axios.ts          # Instancia Axios con interceptores JWT
│       │   ├── auth.ts           # Llamadas a /auth/*
│       │   ├── tasks.ts          # Llamadas a /tasks/*
│       │   ├── wallet.ts         # Llamadas a /wallet/*
│       │   └── profile.ts        # Llamadas a /profile/*
│       │
│       ├── store/
│       │   ├── authStore.ts      # Zustand: user, token, login, logout
│       │   └── taskStore.ts      # Zustand: currentAssignment, progress
│       │
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── RegisterPage.tsx
│       │   ├── DashboardPage.tsx
│       │   ├── TasksPage.tsx
│       │   ├── TaskDetailPage.tsx
│       │   ├── ProcessingPage.tsx
│       │   ├── WalletPage.tsx
│       │   └── ProfilePage.tsx
│       │
│       ├── components/
│       │   ├── ui/               # Primitivas reutilizables (Button, Badge, Card, Spinner, Alert)
│       │   ├── layout/           # Navbar, Sidebar, PageWrapper
│       │   ├── tasks/            # TaskCard, TaskFilters, TaskStatusBadge
│       │   ├── processing/       # ProgressStepper, StageIndicator
│       │   ├── wallet/           # TransactionRow, WithdrawModal, BalanceCard
│       │   └── profile/          # TrustScoreBreakdown, HardwareForm, RankBadge
│       │
│       ├── hooks/
│       │   ├── useAuth.ts        # Wrapper sobre authStore + navegacion
│       │   ├── useTaskProgress.ts # Polling con setInterval, limpieza en unmount
│       │   └── useWallet.ts
│       │
│       ├── types/
│       │   └── index.ts          # Interfaces TypeScript: Provider, Task, Assignment, Wallet, Transaction
│       │
│       └── __tests__/
│           ├── pages/
│           └── components/
│
└── backend/
    ├── requirements.txt
    ├── requirements-dev.txt      # pytest, httpx, ruff, coverage
    ├── pyproject.toml            # Configuracion de Ruff y pytest
    ├── .env.example
    │
    ├── app/
    │   ├── main.py               # FastAPI app, CORS, inclusion de routers, lifespan
    │   │
    │   ├── core/
    │   │   ├── config.py         # Pydantic BaseSettings: lee .env
    │   │   ├── security.py       # create_access_token, verify_token, hash_password, verify_password
    │   │   └── dependencies.py   # get_current_provider (FastAPI Depends)
    │   │
    │   ├── db/
    │   │   ├── client.py         # Singleton Supabase client (service_role key)
    │   │   └── queries/          # Modulos SQL por dominio (auth_queries, task_queries, etc.)
    │   │
    │   ├── routers/
    │   │   ├── auth.py
    │   │   ├── tasks.py
    │   │   ├── wallet.py
    │   │   └── profile.py
    │   │
    │   ├── models/
    │   │   ├── auth.py           # RegisterRequest, LoginRequest, TokenResponse
    │   │   ├── task.py           # Task, TaskAssignment, ProgressResponse
    │   │   ├── wallet.py         # Wallet, Transaction, WithdrawRequest
    │   │   └── profile.py        # ProviderProfile, HardwareUpdate, TrustScoreDetail
    │   │
    │   ├── services/
    │   │   ├── trust_score.py    # Calculo de trust score y logica de rango
    │   │   ├── task_lifecycle.py # Transiciones de estado + actualizacion de wallet
    │   │   └── progress.py       # Calculo de progreso simulado
    │   │
    │   └── seed/
    │       ├── tasks_seed.sql
    │       └── seed.py
    │
    └── tests/
        ├── conftest.py           # TestClient, override de dependencias, DB de test
        ├── test_auth.py
        ├── test_tasks.py
        ├── test_wallet.py
        └── test_profile.py
```

---

## 5. Estrategia de Entornos

### 5.1 Variables de Entorno

Se usa un unico fichero `.env` por entorno. Nunca se versiona. El repositorio incluye `.env.example` con todas las claves documentadas y sin valores reales.

**Backend `.env`:**
```
# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project>.supabase.co:6543/postgres

# JWT
JWT_SECRET_KEY=<min_32_chars_random_string>
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# CORS
FRONTEND_URL=http://localhost:5173

# App
ENVIRONMENT=development
```

**Frontend `.env`:**
```
VITE_API_URL=http://localhost:8000
```

### 5.2 Entorno de Desarrollo (local)

| Componente | Comando | Puerto |
|-----------|---------|--------|
| Backend | `uvicorn app.main:app --reload --port 8000` | 8000 |
| Frontend | `npm run dev` | 5173 |
| Base de datos | Supabase Cloud (proyecto de desarrollo) | remoto |

No se usa Docker en desarrollo local para minimizar el tiempo de arranque (requisito: cold start < 5 minutos).

### 5.3 Entorno de Produccion

| Componente | Plataforma sugerida | Notas |
|-----------|---------------------|-------|
| Backend | Railway o Render (free tier) | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Frontend | Vercel o Netlify | Build output: `dist/` |
| Base de datos | Supabase Cloud (proyecto dedicado prod) | Connection pooling activado |

Las variables de entorno de produccion se configuran en el panel de la plataforma de deployment, nunca en ficheros commiteados.

ENVIRONMENT=production activa: desactivar reload de Uvicorn, nivel de log WARNING, desactivar docs de OpenAPI (`/docs` y `/redoc`).

---

## 6. Dependencias Principales con Versiones

### Backend (`requirements.txt`)

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic[email]==2.9.2
pydantic-settings==2.6.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
supabase==2.10.0
psycopg2-binary==2.9.10
python-multipart==0.0.12
```

### Backend dev (`requirements-dev.txt`)

```
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
pytest-cov==6.0.0
ruff==0.6.9
```

### Frontend (`package.json` — dependencias clave)

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "axios": "^1.7.7",
    "zustand": "^4.5.5",
    "@headlessui/react": "^1.7.19",
    "@heroicons/react": "^2.1.5",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4"
  },
  "devDependencies": {
    "vite": "^5.4.10",
    "@vitejs/plugin-react": "^4.3.3",
    "typescript": "^5.6.3",
    "tailwindcss": "^3.4.14",
    "postcss": "^8.4.47",
    "autoprefixer": "^10.4.20",
    "vitest": "^2.1.4",
    "@vitest/ui": "^2.1.4",
    "@testing-library/react": "^16.0.1",
    "@testing-library/user-event": "^14.5.2",
    "eslint": "^9.13.0",
    "prettier": "^3.3.3",
    "jsdom": "^25.0.1"
  }
}
```

---

## 7. Estrategia de Tests

### 7.1 Backend (pytest)

**Objetivo:** 100% de endpoints principales cubiertos (requisito no negociable del brief).

**Configuracion (`pyproject.toml`):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"

[tool.ruff]
line-length = 100
target-version = "py312"
```

**Estrategia de aislamiento:**
- `conftest.py` crea un `TestClient` de FastAPI con override de `get_current_provider` para tests autenticados.
- Las queries a base de datos se mockean via `unittest.mock.patch` sobre los modulos de `app/db/queries/`. No se usa una base de datos de test real para evitar dependencias de red en CI.
- Cada fichero de test cubre un router completo: happy paths + casos de error (401, 404, 422, 400).

**Cobertura minima por modulo:**

| Modulo | Tests obligatorios |
|--------|-------------------|
| `test_auth.py` | register (ok, email duplicado, password corto), login (ok, credenciales incorrectas), me (ok, token invalido) |
| `test_tasks.py` | list (ok, con filtros), detail (ok, no encontrado), accept, start, complete, fail, history |
| `test_wallet.py` | balance (ok), transactions (ok, paginado), withdraw (ok, saldo insuficiente) |
| `test_profile.py` | stats (ok), hardware update (ok, validacion), online toggle (ok) |

**Comando:**
```bash
pytest --cov=app --cov-report=html
```

### 7.2 Frontend (Vitest)

**Objetivo:** cobertura de componentes criticos y logica de negocio en hooks.

**Alcance del MVP:**
- Hooks: `useAuth` (login, logout, persistencia de token), `useTaskProgress` (polling, limpieza)
- Componentes: `TrustScoreBreakdown` (render con datos), `TaskFilters` (interaccion), `ProgressStepper` (etapas correctas)
- Stores Zustand: `authStore` (estado inicial, login, logout)

**Configuracion (`vite.config.ts`):**
```ts
test: {
  environment: 'jsdom',
  setupFiles: ['./src/__tests__/setup.ts'],
  globals: true,
}
```

**Comando:**
```bash
npm run test
npm run test:ui   # Vitest UI para desarrollo interactivo
```

---

## 8. Seguridad: Reglas No Negociables

| Aspecto | Implementacion |
|---------|---------------|
| Passwords | `passlib[bcrypt]` con rounds=12. Nunca se almacena la password en claro ni se loguea. |
| JWT | HS256, firmado con `JWT_SECRET_KEY` (min 32 chars, generado con `openssl rand -hex 32`). Validado en `get_current_provider` via FastAPI Depends en todos los endpoints protegidos. |
| CORS | `allow_origins=[settings.FRONTEND_URL]`. Nunca `"*"` en produccion. |
| RLS en Supabase | Activado en todas las tablas. Politicas: `providers` — solo el propio registro; `task_assignments` — solo las del propio provider_id; `wallets` — solo la propia; `transactions` — solo las propias. `tasks` — lectura publica para providers autenticados. |
| Secretos | Ninguna credencial en el codigo fuente. Todo en variables de entorno leidas via `pydantic-settings`. El `.env` esta en `.gitignore`. |
| Headers de seguridad | En produccion se añaden via la plataforma de hosting (Vercel/Railway). En el backend se incluye middleware para `X-Content-Type-Options`, `X-Frame-Options`. |
| Validacion de inputs | Pydantic v2 valida todos los request bodies. Los parametros de query se validan con tipos nativos de FastAPI. |
| SQL injection | Ninguna query construye strings con interpolacion directa. Se usan parametros del SDK de Supabase o queries parametrizadas de psycopg2. |

---

## 9. Convenciones de Codigo

### Backend (Python)

- Python 3.12+.
- Tipado estricto en todas las funciones (type hints obligatorios, mypy-compatible).
- Nombres de modulos en `snake_case`. Clases en `PascalCase`. Constantes en `UPPER_SNAKE_CASE`.
- Cada router usa `APIRouter` con `prefix` y `tags`. Ningun endpoint en `main.py`.
- Los servicios (carpeta `services/`) contienen toda la logica de negocio. Los routers solo orquestan: validan la request, llaman al servicio, devuelven la response.
- Las queries SQL estan en `db/queries/`, nunca inline en routers ni servicios.
- Manejo de errores: se usan `HTTPException` con codigos semanticos. No se exponen mensajes de error de base de datos al cliente.
- Ruff para lint y formato. Ejecutar antes de cada commit: `ruff check . && ruff format .`.

### Frontend (TypeScript / React)

- TypeScript estricto (`strict: true` en tsconfig). Ningun `any` explicito.
- Componentes funcionales con hooks. Ningun componente de clase.
- Nombres de componentes en `PascalCase`. Ficheros de componentes en `PascalCase.tsx`. Hooks en `camelCase` con prefijo `use`.
- Cada pagina es responsable de sus llamadas a la API (via hooks o directamente). Los componentes de presentacion no hacen llamadas HTTP.
- Los tipos compartidos estan en `src/types/index.ts`. No se define un tipo en un componente si se usa en mas de un lugar.
- Todos los strings visibles al usuario en español. Ningun texto en inglés en la UI.
- Estados de carga (`isLoading`), error (`error`) y exito deben manejarse explicitamente en cada operacion asincrona. Ninguna pantalla en blanco sin feedback.
- ESLint + Prettier. Configuracion en `eslint.config.js` y `.prettierrc`.

### Git

- Ramas: `main` (produccion), `develop` (integracion), `feature/<nombre>` (desarrollo).
- Commits en español, formato imperativo: "Añadir endpoint de retiro de cartera".
- Ningun secret ni fichero `.env` en el repositorio. El `.gitignore` esta configurado desde el primer commit.

---

## 10. Flujo de Arranque Local (cold start)

El README debe permitir arrancar el proyecto en menos de 5 minutos siguiendo estos pasos:

1. `git clone <repo> && cd co-computing`
2. Crear proyecto en Supabase Cloud, copiar URL y service_role key.
3. Ejecutar el schema SQL (fichero `backend/app/db/schema.sql`) en el SQL editor de Supabase.
4. Activar RLS y aplicar politicas (fichero `backend/app/db/rls_policies.sql`).
5. Copiar `.env.example` a `.env` en `backend/` y `frontend/` y rellenar los valores.
6. Backend: `cd backend && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt && pip install -r requirements-dev.txt`
7. Seed: `python scripts/seed.py`
8. Arrancar backend: `uvicorn app.main:app --reload --port 8000`
9. Frontend: `cd ../frontend && npm install && npm run dev`
10. Abrir `http://localhost:5173`.

Tiempo estimado: 4-5 minutos con conexion a internet estable.

---

*Documento de arquitectura aprobado para traslado al equipo de desarrollo. Cualquier desviacion de este stack debe ser consultada con el CTO antes de implementarse.*
