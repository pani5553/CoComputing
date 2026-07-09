# Co-Computing — Estructura de Carpetas del Monorepo

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** Software Architect
**Referencias:** `docs/01-stack.md`, `docs/02-backlog.md`, `docs/03-design/`

---

## Árbol completo del repositorio

```
co-computing/
│
├── .env.example                        # Variables de entorno raíz (documentación)
├── .gitignore                          # node_modules/, .env, __pycache__, .venv/, dist/
├── README.md                           # Guía de arranque local (cold start < 5 min)
│
├── frontend/
│   ├── .env.example                    # VITE_API_URL=http://localhost:8000
│   ├── index.html                      # Entry HTML; importa Inter + JetBrains Mono desde Google Fonts
│   ├── vite.config.ts                  # Plugin React, alias @/ → src/, vitest config
│   ├── tsconfig.json                   # strict: true, paths para @/
│   ├── tsconfig.node.json
│   ├── tailwind.config.ts              # Tokens brand/success/danger/warning/info + Inter/JetBrains Mono
│   ├── postcss.config.js
│   ├── eslint.config.js                # ESLint 9 flat config
│   ├── .prettierrc
│   ├── package.json
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   └── src/
│       ├── main.tsx                    # ReactDOM.createRoot, BrowserRouter, QueryClientProvider
│       ├── App.tsx                     # Definición de rutas con React Router v6 + ProtectedRoute
│       │
│       ├── api/
│       │   ├── axios.ts                # Instancia Axios: baseURL=VITE_API_URL, interceptor JWT
│       │   │                           #   → request: adjunta Bearer token desde authStore
│       │   │                           #   → response: captura 401, limpia sesión, redirige /login
│       │   ├── auth.ts                 # register(), login(), getMe()
│       │   ├── tasks.ts                # getTasks(filters), getTask(id), acceptTask(id),
│       │   │                           #   startTask(id), completeTask(id), failTask(id),
│       │   │                           #   getTaskProgress(assignmentId), getMyHistory()
│       │   ├── wallet.ts               # getWallet(), getTransactions(), withdraw(payload)
│       │   └── profile.ts              # getStats(), updateProfile(payload),
│       │                               #   updateHardware(payload), toggleOnline()
│       │
│       ├── store/
│       │   ├── authStore.ts            # Zustand: { user, token, isAuthenticated }
│       │   │                           #   actions: login(token, user), logout(), setUser(user)
│       │   │                           #   middleware: persist → localStorage key "cc-auth"
│       │   └── taskStore.ts            # Zustand: { currentAssignment, progress, stages }
│       │                               #   actions: setAssignment(), clearAssignment(),
│       │                               #            updateProgress(data)
│       │
│       ├── pages/
│       │   ├── LoginPage.tsx           # Ruta: /login
│       │   ├── RegisterPage.tsx        # Ruta: /registro
│       │   ├── DashboardPage.tsx       # Ruta: /dashboard (protegida)
│       │   ├── TasksPage.tsx           # Ruta: /tareas (protegida)
│       │   ├── TaskDetailPage.tsx      # Ruta: /tareas/:id (protegida)
│       │   ├── ProcessingPage.tsx      # Ruta: /procesando/:assignmentId (protegida)
│       │   ├── WalletPage.tsx          # Ruta: /cartera (protegida)
│       │   ├── ProfilePage.tsx         # Ruta: /perfil (protegida)
│       │   └── NotFoundPage.tsx        # Ruta: * (catch-all)
│       │
│       ├── components/
│       │   ├── ui/
│       │   │   ├── Button.tsx          # Variantes: primary | secondary | danger | ghost
│       │   │   │                       #   prop: isLoading → muestra Spinner inline
│       │   │   ├── Badge.tsx           # Variantes genéricas de color + tamaño
│       │   │   ├── Card.tsx            # Wrapper con bg-neutral-900 border-neutral-700
│       │   │   ├── Spinner.tsx         # SVG animate-spin; tamaños sm/md/lg
│       │   │   ├── Alert.tsx           # Variantes: success | error | warning | info
│       │   │   ├── Modal.tsx           # Overlay + focus trap + aria-dialog
│       │   │   ├── Toast.tsx           # Notificación flotante; auto-dismiss 4s
│       │   │   ├── ToastContainer.tsx  # Stack de toasts (máx 3), fixed bottom-right
│       │   │   └── SkeletonCard.tsx    # Skeleton animate-pulse reutilizable
│       │   │
│       │   ├── layout/
│       │   │   ├── Navbar.tsx          # Logo, enlaces nav, RankBadge, dropdown usuario
│       │   │   │                       #   Mobile: menú hamburguesa (Bars3Icon)
│       │   │   ├── PageWrapper.tsx     # max-w-7xl mx-auto px-4 md:px-8 py-8
│       │   │   └── ProtectedRoute.tsx  # HOC: comprueba token en authStore; redirige /login
│       │   │
│       │   ├── tasks/
│       │   │   ├── TaskCard.tsx        # Tarjeta de tarea: tipo, dificultad, HW, recompensa
│       │   │   ├── TaskFilters.tsx     # Panel de filtros: dificultad, hardware, tipo, reward
│       │   │   ├── TaskStatusBadge.tsx # Badge de estado de asignación con animación pulse
│       │   │   └── DifficultyBadge.tsx # Badge fácil/medio/difícil con colores semánticos
│       │   │
│       │   ├── processing/
│       │   │   ├── ProgressStepper.tsx # Lista vertical de etapas (completada/activa/pendiente)
│       │   │   │                       #   Props: stages[], currentStageIndex, progress
│       │   │   └── ProgressBar.tsx     # Barra lineal h-3 con gradiente brand
│       │   │
│       │   ├── wallet/
│       │   │   ├── BalanceCard.tsx     # Tarjeta de saldo individual
│       │   │   ├── TransactionRow.tsx  # Fila de tabla de transacción con color por tipo
│       │   │   └── WithdrawModal.tsx   # Modal 2 pasos: datos → confirmación
│       │   │
│       │   └── profile/
│       │       ├── TrustScoreBreakdown.tsx  # 4 barras de componentes + rango
│       │       │                            #   Props: TrustScoreBreakdownProps
│       │       ├── HardwareForm.tsx         # Formulario CPU/GPU/RAM/storage
│       │       └── RankBadge.tsx            # Badge de rango con icono y color por rango
│       │
│       ├── hooks/
│       │   ├── useAuth.ts              # Wrapper sobre authStore + React Router navigate
│       │   │                           #   Expone: user, token, login(), logout(), isAuthenticated
│       │   ├── useTaskProgress.ts      # setInterval 3000ms → GET progress
│       │   │                           #   Gestiona: failCount, cleanup en unmount,
│       │   │                           #   redirección automática en estado terminal
│       │   └── useWallet.ts            # Carga wallet + transactions; expone refetch
│       │
│       ├── types/
│       │   └── index.ts                # Todas las interfaces TypeScript del dominio:
│       │                               #   Provider, Task, TaskAssignment, ProgressData,
│       │                               #   Wallet, Transaction, WithdrawRequest,
│       │                               #   TrustScoreDetail, TaskFilters, AuthResponse
│       │
│       ├── utils/
│       │   └── format.ts               # formatCC(amount): string → "1.234,56 CC"
│       │                               # formatDate(iso): string → "05 jun 2026 · 14:32"
│       │                               # getRankLabel(rank): string en español
│       │
│       └── __tests__/
│           ├── setup.ts                # @testing-library/jest-dom imports
│           ├── hooks/
│           │   ├── useAuth.test.ts
│           │   └── useTaskProgress.test.ts
│           ├── components/
│           │   ├── TrustScoreBreakdown.test.tsx
│           │   ├── TaskFilters.test.tsx
│           │   └── ProgressStepper.test.tsx
│           └── store/
│               └── authStore.test.ts
│
└── backend/
    ├── requirements.txt                # Dependencias de producción (ver §6 de 01-stack.md)
    ├── requirements-dev.txt            # pytest, httpx, ruff, pytest-cov, pytest-asyncio
    ├── pyproject.toml                  # [tool.pytest], [tool.ruff], [tool.coverage]
    ├── .env.example                    # Variables de entorno backend documentadas
    │
    ├── app/
    │   ├── main.py                     # FastAPI app, CORS, routers, lifespan, security headers
    │   │
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── config.py               # Pydantic BaseSettings: todas las env vars tipadas
    │   │   ├── security.py             # create_access_token(), verify_token(),
    │   │   │                           #   hash_password(), verify_password()
    │   │   └── dependencies.py         # get_current_provider() → FastAPI Depends
    │   │                               #   Extrae y valida JWT del header Authorization
    │   │
    │   ├── db/
    │   │   ├── __init__.py
    │   │   ├── client.py               # Singleton Supabase client con service_role key
    │   │   ├── schema.sql              # CREATE TABLE IF NOT EXISTS para las 5 tablas
    │   │   ├── rls_policies.sql        # ALTER TABLE ENABLE RLS + CREATE POLICY IF NOT EXISTS
    │   │   └── queries/
    │   │       ├── __init__.py
    │   │       ├── auth_queries.py     # get_provider_by_email(), create_provider(),
    │   │       │                       #   create_wallet_for_provider()
    │   │       ├── task_queries.py     # get_tasks(filters), get_task_by_id(),
    │   │       │                       #   get_assignment_by_id(), create_assignment(),
    │   │       │                       #   update_assignment_status(), decrement_slots()
    │   │       ├── wallet_queries.py   # get_wallet(), get_transactions(),
    │   │       │                       #   create_transaction(), update_wallet_balance()
    │   │       └── profile_queries.py  # get_provider_by_id(), update_provider(),
    │   │                               #   update_hardware(), toggle_online()
    │   │
    │   ├── routers/
    │   │   ├── __init__.py
    │   │   ├── auth.py                 # POST /auth/register, POST /auth/login, GET /auth/me
    │   │   ├── tasks.py                # GET /tasks/, GET /tasks/my/history,
    │   │   │                           #   GET /tasks/{id}, POST /tasks/{id}/accept,
    │   │   │                           #   POST /tasks/{id}/start, POST /tasks/{id}/complete,
    │   │   │                           #   POST /tasks/{id}/fail,
    │   │   │                           #   GET /tasks/assignments/{assignment_id}/progress
    │   │   ├── wallet.py               # GET /wallet/, GET /wallet/transactions,
    │   │   │                           #   POST /wallet/withdraw
    │   │   └── profile.py              # GET /profile/stats, PUT /profile/hardware,
    │   │                               #   PATCH /profile/online, PATCH /profile/name
    │   │
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── auth.py                 # RegisterRequest, LoginRequest,
    │   │   │                           #   TokenResponse, ProviderPublic
    │   │   ├── task.py                 # Task, TaskAssignment, TaskAssignmentPublic,
    │   │   │                           #   ProgressResponse, TaskFilters (query params)
    │   │   ├── wallet.py               # Wallet, Transaction, WithdrawRequest,
    │   │   │                           #   WithdrawResponse
    │   │   └── profile.py              # ProviderProfile, HardwareUpdate,
    │   │                               #   TrustScoreDetail, OnlineToggleRequest,
    │   │                               #   NameUpdateRequest
    │   │
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── trust_score.py          # calculate_trust_score(), get_rank(),
    │   │   │                           #   update_accuracy(), update_response_time()
    │   │   ├── task_lifecycle.py       # accept_task(), start_task(), complete_task(),
    │   │   │                           #   fail_task() → orquestan queries + trust_score
    │   │   └── progress.py             # calculate_progress(started_at, duration_max_min)
    │   │                               #   → float (0.0 – 99.0)
    │   │                               # get_current_stage_index(progress, total_stages)
    │   │                               #   → int
    │   │
    │   └── seed/
    │       ├── tasks_seed.sql          # 18 tareas representativas (INSERT ... ON CONFLICT)
    │       └── seed.py                 # Script idempotente; lee .env, ejecuta tasks_seed.sql
    │
    └── tests/
        ├── __init__.py
        ├── conftest.py                 # TestClient, override get_current_provider,
        │                               #   fixtures: mock_provider, mock_task, mock_assignment
        ├── test_auth.py                # 7 casos (ver US-23)
        ├── test_tasks.py               # 9 casos (ver US-24)
        ├── test_wallet.py              # 6 casos (ver US-25)
        └── test_profile.py             # 4 casos (ver US-26)
```

---

## Ficheros raíz relevantes

### `.gitignore`

```
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
htmlcov/
.coverage

# Node
node_modules/
dist/
.cache/

# Entornos
.env
backend/.env
frontend/.env

# IDEs
.vscode/
.idea/
*.swp
```

### `.env.example` (raíz — orientativo; los .env reales van en backend/ y frontend/)

```
# Este fichero es SOLO documentación. Los valores reales van en backend/.env y frontend/.env
# Véase backend/.env.example y frontend/.env.example para instrucciones completas.
```

### `backend/.env.example`

```
# ── Supabase ──────────────────────────────────────────────────────────────────
# URL del proyecto Supabase (panel: Settings → API → Project URL)
SUPABASE_URL=https://<project-ref>.supabase.co

# Clave service_role (panel: Settings → API → service_role). NUNCA exponer al cliente.
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Cadena de conexión directa para psycopg2 (puerto 6543 = pooler)
# Formato: postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
SUPABASE_DB_URL=postgresql://postgres.<project-ref>:<password>@...

# ── JWT ───────────────────────────────────────────────────────────────────────
# Clave secreta mínimo 32 caracteres aleatorios. Generar con: openssl rand -hex 32
JWT_SECRET_KEY=<mínimo_32_chars_aleatorios>
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# ── CORS ──────────────────────────────────────────────────────────────────────
# URL exacta del frontend (sin trailing slash)
FRONTEND_URL=http://localhost:5173

# ── App ───────────────────────────────────────────────────────────────────────
# development | production
# En production: deshabilita /docs, /redoc y activa WARNING log level
ENVIRONMENT=development
```

### `frontend/.env.example`

```
# URL base de la API backend (sin trailing slash)
VITE_API_URL=http://localhost:8000
```

---

## Notas para los desarrolladores

### Orden de creación obligatorio

1. Database Engineer ejecuta `backend/app/db/schema.sql` y `backend/app/db/rls_policies.sql` en Supabase.
2. Backend Dev implementa `app/core/`, `app/db/`, `app/models/`, `app/services/`, `app/routers/`.
3. Frontend Dev implementa en paralelo desde los contratos de `docs/04-api-contracts.md`.
4. Ambos ejecutan sus suites de tests antes de integrar.

### Convención de nombres en queries

Todos los módulos en `app/db/queries/` usan **exclusivamente** parámetros del SDK de Supabase o queries parametrizadas de psycopg2. Cero interpolación de strings con datos del usuario.

### El fichero `app/main.py` registra los routers con los prefijos exactos

```python
app.include_router(auth_router,    prefix="/auth",    tags=["auth"])
app.include_router(tasks_router,   prefix="/tasks",   tags=["tasks"])
app.include_router(wallet_router,  prefix="/wallet",  tags=["wallet"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])
```

El middleware de seguridad añade `X-Content-Type-Options: nosniff` y `X-Frame-Options: DENY` a todas las respuestas.

---

## Estructura adicional — Feature "Cómputo Real Distribuido"

Los siguientes ficheros y directorios se añaden al árbol existente. No se modifica ni elimina ningún fichero de la estructura anterior.

### Nuevos módulos en `backend/`

```
backend/
│
├── app/
│   │
│   ├── routers/
│   │   ├── compute.py          # Router de /jobs (lado cliente)
│   │   │                       #   POST /jobs
│   │   │                       #   GET  /jobs
│   │   │                       #   GET  /jobs/{job_id}
│   │   │                       #   GET  /jobs/{job_id}/result
│   │   └── work.py             # Router de /work (lado worker)
│   │                           #   POST /work/claim
│   │                           #   POST /work/{chunk_id}/submit
│   │
│   ├── models/
│   │   └── compute.py          # Pydantic models: JobCreateRequest, JobPublic,
│   │                           #   JobListResponse, ChunkWithPayload, ClaimRequest,
│   │                           #   ClaimResponse, SubmitRequest, SubmitResponse
│   │
│   ├── services/
│   │   ├── compute_service.py  # create_job(), list_jobs(), get_job(), get_job_result(),
│   │   │                       #   finalize_job(), split_csv()
│   │   └── consensus_service.py  # evaluate_chunk(): lógica de consenso, pago y trust
│   │
│   ├── db/
│   │   └── queries/
│   │       └── compute_queries.py  # Todas las queries para jobs, chunks, chunk_results.
│   │                               # claim_chunks_atomic() usa psycopg2 con
│   │                               # FOR UPDATE SKIP LOCKED (no SDK Supabase).
│   │
│   └── worker/
│       ├── __init__.py
│       ├── main.py             # Entry point: python -m app.worker
│       │                       #   --api  URL de la API (default: http://localhost:8000)
│       │                       #   --email  Email del proveedor/worker
│       │                       #   --password  Password del proveedor/worker
│       │                       #   --poll-interval  Segundos entre polls (default: 5)
│       │                       #   --max-chunks  Chunks por claim (default: 3)
│       └── plugins/
│           ├── __init__.py     # PLUGINS dict: {"data-processing": DataProcessingPlugin}
│           │                   # Función get_plugin(job_type) -> WorkerPlugin
│           ├── base.py         # Clase abstracta WorkerPlugin con método process(payload)
│           └── data_processing.py  # DataProcessingPlugin: usa polars para mean/sum/min/max/count
│
├── tests/
│   ├── test_compute.py         # Tests del router /jobs (casos C-01 a C-05)
│   └── test_consensus.py       # Tests del servicio de consenso (casos K-01 a K-07)
│
└── scripts/
    └── run_workers.sh          # Lanza 3 instancias del worker en paralelo para demo
                                # Requiere WORKER_EMAIL y WORKER_PASSWORD como env vars
```

### Nuevos ficheros en `frontend/`

```
frontend/src/
│
├── api/
│   └── compute.ts              # createJob(formData), listJobs(status?), getJob(id),
│                               #   getJobResult(id)
│
├── types/
│   └── compute.ts              # Interfaces TypeScript: Job, JobStatus, ChunkStatus,
│                               #   ClaimResponse, ChunkWithPayload, SubmitRequest,
│                               #   SubmitResponse, JobCreateRequest, JobListResponse
│
├── store/
│   └── jobStore.ts             # Zustand: { jobs, currentJob }
│                               #   actions: setJobs(), setCurrentJob(), updateJobProgress()
│                               #   middleware: NO persiste (datos volátiles)
│
├── pages/
│   ├── JobsPage.tsx            # Ruta: /trabajos (protegida)
│   │                           #   Lista de jobs del cliente con estado y progreso real
│   │                           #   Botón "Nuevo trabajo" → abre modal o navega a /trabajos/nuevo
│   └── NewJobPage.tsx          # Ruta: /trabajos/nuevo (protegida)
│                               #   Formulario: subir CSV + elegir operación + columnas
│                               #   Reusa Button, Card, Spinner, Alert existentes
│
├── components/
│   └── jobs/
│       ├── JobCard.tsx         # Tarjeta de job: tipo, estado (badge), progreso (ProgressBar)
│       │                       #   Props: job: Job
│       ├── JobStatusBadge.tsx  # Badge con color semántico por JobStatus
│       │                       #   pending/splitting → gris, processing → azul,
│       │                       #   validating → amarillo, completed → verde, failed → rojo
│       ├── JobResultView.tsx   # Visualización del resultado consolidado (tabla/JSON)
│       │                       #   Props: result: Record<string, unknown>
│       └── CsvUploadForm.tsx   # Formulario de subida: input[type=file] + select operación
│                               #   + multiselect columnas (lectura previa de cabeceras CSV)
│                               #   Reusa Button, Spinner, Alert existentes
│
└── hooks/
    └── useJobProgress.ts       # setInterval 5000ms → GET /jobs/{id}
                                #   Gestiona cleanup en unmount
                                #   Para cuando status = 'completed' | 'failed'
```

### Actualización de `app/main.py` (dos líneas a añadir al bloque de imports y registration)

```python
# Añadir al bloque de imports en app/main.py
from app.routers import compute, work   # junto a los imports existentes: auth, profile, tasks, wallet

# Añadir al bloque de router registration
app.include_router(compute.router, prefix="/jobs",  tags=["compute"])
app.include_router(work.router,    prefix="/work",  tags=["work"])
```

### Actualización del orden de creación

El orden de trabajo para la nueva feature es:

1. Database Engineer verifica que `migrations/004_compute.sql` está ejecutado en Supabase.
2. Backend Dev implementa en este orden:
   a. `app/models/compute.py` (Pydantic models)
   b. `app/db/queries/compute_queries.py` (queries, incluyendo `claim_chunks_atomic` con psycopg2)
   c. `app/services/compute_service.py` (split + create_job + finalize_job)
   d. `app/services/consensus_service.py` (evaluate_chunk)
   e. `wallet_service.credit_reward()` — función nueva a añadir en el servicio existente
   f. `app/routers/compute.py` y `app/routers/work.py`
   g. Registro en `app/main.py`
   h. `app/worker/` completo
3. Frontend Dev implementa en paralelo desde los contratos de `docs/04-api-contracts.md §6`.
4. Ambos ejecutan sus suites de tests antes de integrar.

### Dependencia nueva en `requirements.txt`

```
polars>=0.20.0
```

La dependencia `polars` solo es necesaria en el proceso worker. Para el backend FastAPI no se importa en el path de inicialización; el import ocurre únicamente dentro de `DataProcessingPlugin.process()`. Esto evita que un error de instalación de polars rompa el arranque de la API.

---

## Estructura adicional — Feature Lado Cliente (Escrow)

Esta estructura ya está implementada (`briefs/03-lado-cliente.md`) pero no había quedado reflejada en este documento; se añade aquí una referencia mínima al detectarse durante la revisión de `briefs/05-vercel-creditos.md` (US-42 / CH-01). Sigue el mismo patrón aditivo que la sección anterior: no se modifica ningún fichero de la estructura ya descrita.

**Backend** — añade el rol "cliente" reutilizando el patrón router → service → repository:

- `app/routers/client.py` — prefijo `/client`: `POST /deposit`, `POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/cancel`.
- `app/services/client_service.py` — `deposit()`, `create_task()`, `get_my_tasks()`, `get_task_detail()`, `cancel_task()`.
- `app/db/queries/client_queries.py` — `deposit_to_wallet()`, `hold_escrow()`, `get_escrow_by_task()`, `release_escrow_slot()`, `refund_escrow()`, `create_client_task()`, `get_client_tasks()`, `get_client_task_detail()`, `cancel_task_db()`.

**Frontend:**

- `src/pages/client/` — `DepositPage.tsx` (ruta `/cliente/recargar`), `PublishTaskPage.tsx` (`/cliente/publicar`), `MyTasksPage.tsx` (`/cliente/mis-tareas`), `ClientTaskDetailPage.tsx` (`/cliente/tareas/:taskId`).
- `src/api/clientApi.ts` — funciones que llaman a los endpoints de `/client`.
- Nota: `api/axios.ts` (así nombrado en el árbol de este documento) fue renombrado a `api/client.ts` durante esta feature para evitar colisión con el nuevo concepto de dominio "cliente"; su contenido (instancia Axios, interceptores JWT y de sesión expirada) no cambió.

**Datos** (`migrations/005_client.sql`): añade `tasks.client_id` (uuid, nullable, FK → `providers`), amplía el `CHECK` de `transactions.tx_type` con `deposito`, `escrow`, `reembolso`, `pago_recibido`, y crea la tabla `escrows` (retención de fondos por tarea publicada: `amount_held`, `amount_released`, `status`).

---

## Estructura adicional — Endurecimiento de Seguridad Pre-Lanzamiento (2026-07-08)

Diseño completo en `docs/04-arquitectura.md` §15 (rate limiting compartido vía Postgres, credenciales del worker por variable de entorno, aislamiento de proceso del worker, mitigación básica de Sybil en registro). Sigue el mismo patrón aditivo que las secciones anteriores: no se modifica ni elimina ningún fichero de la estructura ya descrita.

**Backend — módulos nuevos:**

```
backend/app/
│
├── core/
│   └── rate_limit.py           # check_rate_limit(bucket, limit, window_seconds)
│                                #   rate_limit_by_ip(scope, limit, window_seconds) -> Depends
│                                #   rate_limit_by_provider(scope, limit, window_seconds) -> Depends
│                                #   Contador compartido en Postgres (tabla rate_limit_counters),
│                                #   no en memoria de proceso — ver §15.0 (--workers 2 lo invalidaría)
│
└── worker/
    └── sandbox.py               # run_chunk_sandboxed(job_type, payload) -> (result, duration_ms)
                                  #   Ejecuta plugin.process() en subproceso separado
                                  #   (multiprocessing, contexto "spawn") con timeout duro
                                  #   (30s) y límites de CPU/memoria (módulo `resource`, POSIX)
                                  #   Primer paso de aislamiento — NO sandboxing completo
                                  #   (sin contenedores/seccomp), ver §15.3.5
```

**Backend — ficheros existentes modificados (sin cambio de estructura de carpetas):**

- `app/routers/auth.py` — añade `dependencies=[Depends(rate_limit_by_ip(...))]` en `POST /register` y `POST /login`.
- `app/routers/work.py` — sustituye `Depends(get_current_provider)` por `Depends(rate_limit_by_provider(...))` en `POST /claim` y `POST /{chunk_id}/submit`.
- `app/models/auth.py` — `RegisterRequest` gana un `field_validator` de email (normaliza a minúsculas, rechaza puntos consecutivos / parte local excesiva).
- `app/worker/main.py` — nueva función `resolve_worker_credentials()`; `--email`/`--password` pasan a opcionales (deprecados) en favor de `CC_WORKER_EMAIL`/`CC_WORKER_PASSWORD`; `process_chunk()` delega en `sandbox.run_chunk_sandboxed()`.
- `app/worker/run_workers.sh` — elimina el default inseguro `password123`; exige `CC_WORKER_PASSWORD` del entorno.

**Datos** (`migrations/008_rate_limiting.sql`, contenido exacto en `docs/04-arquitectura.md` §15.1.2): crea la tabla `rate_limit_counters (bucket, window_start, request_count)`. Sin RLS (acceso exclusivo vía psycopg2 directo). Documentada en `docs/04-api-contracts.md` §1.7.

**Variables de entorno nuevas (worker, no del backend FastAPI):** `CC_WORKER_EMAIL`, `CC_WORKER_PASSWORD` — sustituyen a los argumentos CLI `--email`/`--password` (deprecados, no eliminados este ciclo). No se añade ninguna variable de entorno nueva al backend ni a `backend/.env.example`.

**Sin cambios en `frontend/`:** ninguna de las 4 decisiones de este ciclo toca el frontend.
