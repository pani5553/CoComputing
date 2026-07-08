# Co-Computing — Arquitectura Técnica Detallada

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** Software Architect
**Referencias:** `docs/01-stack.md`, `docs/04-api-contracts.md`, `docs/04-estructura.md`

---

## 1. Diagrama de Arquitectura

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        NAVEGADOR DEL PROVEEDOR                           │
│                                                                          │
│  React 18 SPA (Vite 5.4) — TypeScript strict                            │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │  Zustand    │  │  React Router│  │  Axios Instance                │  │
│  │  authStore  │  │  v6          │  │  baseURL = VITE_API_URL         │  │
│  │  taskStore  │  │  BrowserRouter│ │  interceptor: Bearer JWT        │  │
│  └──────┬──────┘  └──────┬───────┘  │  interceptor: 401 → logout     │  │
│         │                │          └────────────────┬───────────────┘  │
│         └────────────────┴───────────────────────────┘                  │
│                                      │                                  │
│  Rutas públicas:   /login  /registro                                    │
│  Rutas protegidas: /dashboard  /tareas  /tareas/:id                     │
│                    /procesando/:id  /cartera  /perfil                   │
│                                                                          │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │ HTTPS REST JSON
                                       │ Authorization: Bearer <HS256 JWT>
                                       │ Content-Type: application/json
┌──────────────────────────────────────▼───────────────────────────────────┐
│                      FASTAPI + UVICORN (puerto 8000)                     │
│                                                                          │
│  app/main.py                                                             │
│  ├── CORSMiddleware: allow_origins=[FRONTEND_URL]                        │
│  ├── SecurityHeadersMiddleware: X-Content-Type-Options, X-Frame-Options  │
│  └── Routers incluidos con prefijo:                                      │
│       /auth  /tasks  /wallet  /profile                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  CAPA ROUTER  (app/routers/)                                        │ │
│  │  Responsabilidad: recibir HTTP, validar con Pydantic, llamar        │ │
│  │  al servicio, devolver respuesta. Sin lógica de negocio aquí.       │ │
│  │                                                                     │ │
│  │  auth.py   tasks.py   wallet.py   profile.py                        │ │
│  │  ↓ Depends(get_current_provider) en todos los endpoints [AUTH]      │ │
│  └─────────────────────┬───────────────────────────────────────────────┘ │
│                         │                                                │
│  ┌─────────────────────▼───────────────────────────────────────────────┐ │
│  │  CAPA SERVICE  (app/services/)                                      │ │
│  │  Responsabilidad: lógica de negocio, orquestación de queries,       │ │
│  │  cálculos (Trust Score, progreso), transacciones lógicas.           │ │
│  │                                                                     │ │
│  │  trust_score.py   task_lifecycle.py   progress.py                   │ │
│  └─────────────────────┬───────────────────────────────────────────────┘ │
│                         │                                                │
│  ┌─────────────────────▼───────────────────────────────────────────────┐ │
│  │  CAPA REPOSITORY  (app/db/queries/)                                 │ │
│  │  Responsabilidad: acceso a datos. SQL parametrizado via SDK         │ │
│  │  Supabase o psycopg2. Cero lógica de negocio.                       │ │
│  │                                                                     │ │
│  │  auth_queries.py   task_queries.py   wallet_queries.py              │ │
│  │  profile_queries.py                                                 │ │
│  └─────────────────────┬───────────────────────────────────────────────┘ │
│                         │                                                │
│  ┌─────────────────────▼───────────────────────────────────────────────┐ │
│  │  DB CLIENT  (app/db/client.py)                                      │ │
│  │  Singleton Supabase client inicializado con service_role key.       │ │
│  │  La service_role key bypasea RLS (uso controlado).                  │ │
│  └─────────────────────┬───────────────────────────────────────────────┘ │
└─────────────────────────┼────────────────────────────────────────────────┘
                          │ Supabase Python SDK (puerto 443)
                          │ psycopg2 pooled connection (puerto 6543)
┌─────────────────────────▼────────────────────────────────────────────────┐
│                    SUPABASE (PostgreSQL 15 Cloud)                        │
│                                                                          │
│  Tablas: providers, tasks, task_assignments, wallets, transactions       │
│                                                                          │
│  Row Level Security activado en las 5 tablas                            │
│  Políticas: cada proveedor accede solo a sus propios registros           │
│  La service_role key del backend bypasea RLS de forma controlada         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Capas del Backend

### 2.1 Capa Router

Los routers (`app/routers/*.py`) tienen una única responsabilidad:

1. Declarar la ruta HTTP con su método, prefijo y decorador FastAPI.
2. Inyectar dependencias (proveedor autenticado via `Depends(get_current_provider)`).
3. Llamar al servicio correspondiente con los parámetros validados.
4. Devolver la respuesta con el código HTTP correcto.

**Lo que los routers NO hacen:** cálculos de negocio, queries directas a la base de datos, lógica condicional compleja.

Ejemplo del contrato interno:

```python
# routers/tasks.py
@router.post("/{task_id}/complete", response_model=CompleteTaskResponse)
async def complete_task(
    task_id: UUID,
    provider: Provider = Depends(get_current_provider),
) -> CompleteTaskResponse:
    return await task_lifecycle.complete_task(task_id=task_id, provider=provider)
```

### 2.2 Capa Service

Los servicios (`app/services/*.py`) contienen toda la lógica de negocio:

- **`task_lifecycle.py`**: Orquestra las transiciones de estado de una asignación. Valida que la transición sea permitida, actualiza la asignación, actualiza la wallet (en complete), llama a `trust_score.py` para recalcular, y crea la transacción correspondiente. Todas las operaciones relacionadas con una transición forman una unidad lógica (se orquestan en secuencia; si una falla, lanza HTTPException).

- **`trust_score.py`**: Implementa la fórmula ponderada, actualiza los componentes (`accuracy`, `response_time_score`) y asigna el rango. No hace queries directas; recibe y devuelve datos.

- **`progress.py`**: Calcula el progreso simulado a partir del tiempo transcurrido. Función pura, sin acceso a base de datos.

### 2.3 Capa Repository

Los módulos en `app/db/queries/*.py` encapsulan el acceso a datos:

- Reciben parámetros tipados.
- Ejecutan queries parametrizadas (nunca interpolación de strings).
- Devuelven diccionarios o `None`.
- No contienen lógica de negocio ni validación.

**Patron de uso del SDK de Supabase:**

```python
# Correcto — parámetros binding del SDK
result = supabase.table("tasks") \
    .select("*") \
    .eq("status", "disponible") \
    .gt("slots_left", 0) \
    .order("reward", desc=True) \
    .limit(50) \
    .execute()

# NUNCA — interpolación de string
query = f"SELECT * FROM tasks WHERE status = '{status}'"  # SQL injection
```

---

## 3. Middleware de Autenticación JWT

### 3.1 Flujo de validación

```
Request entrante con header: Authorization: Bearer <token>
                    │
                    ▼
        app/core/dependencies.py
        get_current_provider(token: str = Depends(oauth2_scheme))
                    │
                    ▼
        security.verify_token(token)
        ├── jose.jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        ├── Extrae claim "sub" (provider UUID)
        ├── Si decode falla (expirado, firma inválida, malformado):
        │       raise HTTPException(401, "No autenticado")
        └── Devuelve provider_id (str)
                    │
                    ▼
        auth_queries.get_provider_by_id(provider_id)
        ├── Si no existe en BD:
        │       raise HTTPException(401, "No autenticado")
        └── Devuelve Provider model
                    │
                    ▼
        Provider inyectado en el endpoint como parámetro
```

### 3.2 Implementación en `app/core/security.py`

```python
JWT_SECRET_KEY: str          # desde settings (min 32 chars)
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_DAYS: int = 7

def create_access_token(subject: str) -> str:
    """Crea JWT con claim sub=subject y exp=ahora+7días."""
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "iat": datetime.utcnow()}
    return jose.jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> str:
    """Valida JWT y devuelve el claim sub. Lanza ValueError si inválido."""
    payload = jose.jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    return payload["sub"]

def hash_password(password: str) -> str:
    """Hashea con bcrypt, rounds=12."""
    return passlib.hash.bcrypt.using(rounds=12).hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return passlib.hash.bcrypt.verify(plain, hashed)
```

### 3.3 Endpoints excluidos de autenticación

Solo dos endpoints son públicos:
- `POST /auth/register`
- `POST /auth/login`

Todos los demás usan `Depends(get_current_provider)`.

---

## 4. Manejo de Errores HTTP

### 4.1 Jerarquía de errores

```
HTTPException (FastAPI)
    ├── 400 Bad Request   → Reglas de negocio violadas
    ├── 401 Unauthorized  → JWT ausente, expirado o inválido
    ├── 403 Forbidden     → Recurso existe pero no pertenece al proveedor
    ├── 404 Not Found     → Recurso no existe
    ├── 409 Conflict      → Violación de unicidad (email duplicado)
    └── 422 Unprocessable → Validación Pydantic (automático)

Exception no controlada → 500 Internal Server Error
    → El handler global captura, loguea en nivel ERROR y devuelve
      {"detail": "Error interno del servidor"}
    → NUNCA expone stack traces ni mensajes de BD al cliente
```

### 4.2 Handler global de errores en `app/main.py`

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"}
    )
```

### 4.3 Regla de oro: no exponer detalles internos

Los mensajes de error de Supabase, psycopg2 o Python nunca llegan al cliente. El servicio captura la excepción interna, la loguea, y lanza un `HTTPException` con un mensaje legible en español.

---

## 5. Estrategia de Simulación de Progreso de Tareas

### 5.1 Diseño

El procesamiento real de cómputo está fuera del alcance del MVP. La simulación se implementa como un cálculo determinístico en el backend basado en tiempo transcurrido:

```
progress(t) = min((t / T_max) × 100, 99.0)
```

Donde:
- `t` = segundos transcurridos desde `task_assignments.started_at`
- `T_max` = `tasks.duration_max × 60` (en segundos)
- El techo de `99.0` garantiza que el proveedor siempre debe pulsar "Completar"

### 5.2 Flujo completo

```
POST /tasks/{id}/start
    └── Registra started_at = now() en task_assignments
    └── Devuelve stages[], stages_count, duration_max_seconds al frontend

GET /tasks/assignments/{id}/progress  (cada 3 segundos)
    └── Calcula elapsed = now() - started_at
    └── progress = min((elapsed / duration_max_seconds) * 100, 99.0)
    └── current_stage_index = min(floor(progress/100 * N_stages), N_stages-1)
    └── can_complete = progress >= 80.0
    └── Devuelve todo en < 200ms (cálculo en memoria, 1 query a BD)

POST /tasks/{id}/complete
    └── Proveedor confirma manualmente cuando progress >= 80%
    └── Transiciona a "completada", acredita recompensa
```

### 5.3 Por qué el techo es 99% y no 100%

El progreso del 100% solo ocurre cuando el backend pone la asignación en estado `completada` (tras la confirmación del proveedor). Hasta ese momento, el endpoint de progreso nunca devuelve 100.0. Esto refleja la semántica de que el proveedor es quien decide cuándo el trabajo está terminado, evita completados automáticos no supervisados y da una sensación de control al usuario.

### 5.4 Etapas derivadas del progreso

```python
# services/progress.py
def get_current_stage_index(progress: float, total_stages: int) -> int:
    if total_stages == 0:
        return 0
    # Nunca desborda: aunque progress sea 99.0, el índice no supera el último
    index = int((progress / 100.0) * total_stages)
    return min(index, total_stages - 1)
```

---

## 6. Row Level Security en Supabase

### 6.1 Arquitectura de acceso

El backend usa la `service_role key` de Supabase, que bypasea RLS. Sin embargo, las políticas RLS están activas como segunda línea de defensa: si en el futuro se añade un cliente directo al SDK (frontend conectando directamente a Supabase), las políticas protegen los datos automáticamente.

La validación de pertenencia (proveedor A no puede completar la asignación de proveedor B) se implementa explícitamente en `app/services/task_lifecycle.py` comparando `assignment.provider_id == current_provider.id`.

### 6.2 Políticas RLS por tabla

**`providers`** — Cada proveedor solo puede leer y actualizar su propio registro:
```sql
-- Política de lectura
CREATE POLICY "providers_select_own" ON providers
  FOR SELECT USING (auth.uid()::text = id::text);

-- Política de actualización
CREATE POLICY "providers_update_own" ON providers
  FOR UPDATE USING (auth.uid()::text = id::text);
```

**`tasks`** — Lectura pública para todos los proveedores autenticados; inserción solo via service_role (seed):
```sql
CREATE POLICY "tasks_select_authenticated" ON tasks
  FOR SELECT USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
```

**`task_assignments`** — Cada proveedor solo accede a sus propias asignaciones:
```sql
CREATE POLICY "assignments_select_own" ON task_assignments
  FOR SELECT USING (auth.uid()::text = provider_id::text);

CREATE POLICY "assignments_insert_own" ON task_assignments
  FOR INSERT WITH CHECK (auth.uid()::text = provider_id::text);

CREATE POLICY "assignments_update_own" ON task_assignments
  FOR UPDATE USING (auth.uid()::text = provider_id::text);
```

**`wallets`** — Cada proveedor solo accede a su propia cartera:
```sql
CREATE POLICY "wallets_select_own" ON wallets
  FOR SELECT USING (auth.uid()::text = provider_id::text);

CREATE POLICY "wallets_update_own" ON wallets
  FOR UPDATE USING (auth.uid()::text = provider_id::text);
```

**`transactions`** — Cada proveedor solo accede a sus propias transacciones:
```sql
CREATE POLICY "transactions_select_own" ON transactions
  FOR SELECT USING (auth.uid()::text = provider_id::text);
```

### 6.3 Nota importante sobre `auth.uid()`

Dado que la autenticación de Co-Computing es propia (JWT HS256 en FastAPI, NO Supabase Auth), la función `auth.uid()` de Supabase **no estará disponible** en el contexto habitual. Las políticas RLS descritas arriba son el estado objetivo para el caso de que se migre a Supabase Auth en el futuro, o si se usa el SDK cliente desde el navegador.

Para el MVP, la seguridad de acceso se garantiza al 100% en la capa de servicio de FastAPI. El fichero `rls_policies.sql` debe documentar explícitamente esta situación y habilitar RLS con una política `service_role_bypass` por defecto.

---

## 7. Variables de Entorno Completas

### 7.1 Backend (`backend/.env`)

```bash
# ── Supabase ──────────────────────────────────────────────────────────────────
# URL del proyecto. Panel Supabase: Settings → API → Project URL
SUPABASE_URL=https://<project-ref>.supabase.co

# Clave service_role. Panel Supabase: Settings → API → service_role key
# NUNCA exponer al navegador. Solo backend.
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Cadena de conexión al pool de conexiones de Supabase (puerto 6543, no 5432)
# Formato: postgresql://postgres.<project-ref>:<db-password>@aws-0-<region>.pooler.supabase.com:6543/postgres
SUPABASE_DB_URL=postgresql://postgres.abcdef:mipassword@aws-0-eu-west-1.pooler.supabase.com:6543/postgres

# ── JWT ───────────────────────────────────────────────────────────────────────
# Mínimo 32 caracteres. Generar: openssl rand -hex 32
JWT_SECRET_KEY=a3f8b2c9d1e4f7a0b3c6d9e2f5a8b1c4d7e0f3a6b9c2d5e8f1a4b7c0d3e6f9a2
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# ── CORS ──────────────────────────────────────────────────────────────────────
# URL exacta del frontend sin trailing slash
# Producción: https://co-computing.vercel.app
FRONTEND_URL=http://localhost:5173

# ── Aplicación ────────────────────────────────────────────────────────────────
# development: activa /docs y /redoc, log level DEBUG
# production:  desactiva /docs y /redoc, log level WARNING
ENVIRONMENT=development
```

### 7.2 Frontend (`frontend/.env`)

```bash
# URL base del backend sin trailing slash
# Producción: https://co-computing.railway.app
VITE_API_URL=http://localhost:8000
```

### 7.3 Lectura de variables en `app/core/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7
    frontend_url: str
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

settings = Settings()
```

---

## 8. Decisiones de Arquitectura

### 8.1 JWT propio en FastAPI, no Supabase Auth

**Decisión:** La autenticación se implementa completamente en FastAPI con `python-jose` y `passlib`. Supabase se usa solo como base de datos.

**Motivo:** El brief especifica explícitamente JWT HS256 con expiración de 7 días. Supabase Auth usa RS256 y gestiona tokens en su propio servicio, lo cual entraría en conflicto con el requisito. La implementación propia es más directa y da control total sobre el payload del token.

**Implicación para RLS:** Como se explica en §6.3, las políticas RLS basadas en `auth.uid()` no son aplicables con JWT propio. La seguridad de acceso la garantiza la capa de servicio de FastAPI.

### 8.2 Monorepo sin Turborepo

**Decisión:** Directorio raíz `co-computing/` con `frontend/` y `backend/` en el mismo repositorio.

**Motivo:** Un solo equipo, un solo producto. El overhead operativo de Turborepo o Nx no aporta valor para un MVP de este tamaño. El arranque local en < 5 minutos es un requisito no negociable.

### 8.3 Sin SQLAlchemy

**Decisión:** Supabase Python SDK para CRUD estándar y psycopg2 para queries complejas.

**Motivo:** Evita una capa de abstracción extra. El SDK de Supabase ya proporciona una API fluida para CRUD. Para queries con JOINs (historial con nombre de tarea, stats del dashboard) se usa psycopg2 con queries parametrizadas directamente.

### 8.4 Tres servicios, responsabilidades claras

| Servicio | Responsabilidad única |
|----------|----------------------|
| `trust_score.py` | Fórmula ponderada y lógica de rango. Función pura: entrada = datos del proveedor, salida = nuevos valores. |
| `task_lifecycle.py` | Orquestación de transiciones de estado. Coordina queries, wallet, trust score y transacciones en la secuencia correcta. |
| `progress.py` | Cálculo de progreso simulado. Función pura: entrada = timestamps + duración, salida = float. |

### 8.5 Polling vs WebSockets para progreso

**Decisión:** Polling HTTP cada 3 segundos desde el frontend.

**Motivo:** WebSockets requieren infraestructura adicional (Railway/Render soportan WebSockets pero aumentan la complejidad de despliegue). El polling a 3s es suficiente para una experiencia de progreso convincente. El requisito de respuesta < 200ms del endpoint `/progress` es alcanzable con el cálculo en memoria.

**Mitigación de carga:** El endpoint de progreso realiza exactamente 1 query a la base de datos (obtener la asignación con `started_at` y el task con `duration_max`). El cálculo del porcentaje es aritmética pura en memoria.

### 8.6 Orden de rutas en FastAPI para `/tasks`

FastAPI matchea rutas en orden de registro. Las rutas literales deben registrarse antes que las rutas con parámetros para evitar que `/tasks/my/history` sea interpretado como `/tasks/{task_id}` con `task_id = "my"`.

**Orden correcto en `routers/tasks.py`:**

```python
# 1. Rutas literales primero
router.get("/my/history")
router.get("/assignments/{assignment_id}/progress")

# 2. Rutas con parámetros después
router.get("/{task_id}")
router.post("/{task_id}/accept")
router.post("/{task_id}/start")
router.post("/{task_id}/complete")
router.post("/{task_id}/fail")
```

### 8.7 Operación atómica en `accept_task`

El decremento de `slots_left` debe ser atómico para evitar condiciones de carrera (dos proveedores aceptando la última plaza simultáneamente):

```sql
UPDATE tasks
SET slots_left = slots_left - 1
WHERE id = :task_id AND slots_left > 0
RETURNING slots_left;
```

Si la query devuelve 0 filas (porque `slots_left` ya era 0), se lanza `HTTPException(400, "No quedan plazas disponibles")`.

### 8.8 Transacciones lógicas sin transacciones de base de datos

El MVP no usa transacciones de base de datos explícitas (BEGIN/COMMIT) para mantener la simplicidad. La secuencia de operaciones en `complete_task` es:

1. Verificar que la asignación existe y pertenece al proveedor.
2. Calcular el nuevo Trust Score.
3. Actualizar `task_assignments` (status, reward_paid, trust_delta).
4. Actualizar `wallets` (available_balance, total_earned).
5. Crear `transactions` (pago_tarea).
6. Actualizar `providers` (tasks_completed, trust_score, rank, success_rate, componentes).

Si algún paso falla, el error se propaga como `HTTPException(500)`. En el MVP con un solo usuario activo por request, el riesgo de inconsistencia es bajo. Para producción real se añadiría una transacción explícita con psycopg2.

---

## 9. Estrategia de Tests

### 9.1 Backend (pytest)

**Configuración en `pyproject.toml`:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "UP", "B", "A"]
```

**Estrategia de aislamiento:**

```python
# tests/conftest.py
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.core.dependencies import get_current_provider

# Fixture del proveedor mockeado
@pytest.fixture
def mock_provider():
    return Provider(
        id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        email="test@example.com",
        full_name="Test Provider",
        trust_score=50.00,
        rank="confiable",
        ...
    )

# Override de la dependencia de autenticación
@pytest.fixture
def authenticated_client(mock_provider):
    app.dependency_overrides[get_current_provider] = lambda: mock_provider
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

Todas las queries a la base de datos se mockean via `unittest.mock.patch` sobre los módulos en `app/db/queries/`. No se requiere una base de datos real para los tests.

### 9.2 Frontend (Vitest)

Los tests del frontend cubren la lógica de negocio en hooks y la renderización de componentes críticos. Las llamadas HTTP se mockean con `vi.mock('@/api/tasks')`.

```typescript
// Ejemplo: src/__tests__/hooks/useTaskProgress.test.ts
import { renderHook, act } from '@testing-library/react'
import { vi } from 'vitest'
import * as tasksApi from '@/api/tasks'

vi.mock('@/api/tasks')

test('limpia el intervalo al desmontar', () => {
  vi.useFakeTimers()
  const { unmount } = renderHook(() => useTaskProgress('assignment-id'))
  unmount()
  // Verificar que clearInterval fue llamado
  expect(vi.getTimerCount()).toBe(0)
  vi.useRealTimers()
})
```

---

## 10. Configuración CORS y Headers de Seguridad

### 10.1 CORS en `app/main.py`

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],   # NUNCA ["*"] en producción
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 10.2 Headers de seguridad (middleware custom)

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### 10.3 Configuración según entorno

En `app/main.py`, la documentación automática de OpenAPI solo está disponible en desarrollo:

```python
app = FastAPI(
    title="Co-Computing API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)
```

---

## 11. Handoff para el Database Engineer

### Acciones requeridas (en orden)

**Paso 1 — Ejecutar `schema.sql`** en el SQL Editor de Supabase.

Crea las 5 tablas con todos sus campos, tipos, restricciones CHECK, claves foráneas y triggers de `updated_at`. Usa `CREATE TABLE IF NOT EXISTS` para ser idempotente.

Tablas a crear, en este orden (por dependencias de FK):
1. `providers`
2. `tasks`
3. `wallets` (FK → providers)
4. `task_assignments` (FK → providers, tasks)
5. `transactions` (FK → providers, tasks nullable)

Triggers de `updated_at` en: `providers`, `tasks`, `task_assignments`, `wallets`.

**Paso 2 — Ejecutar `rls_policies.sql`** en el SQL Editor de Supabase.

Activa RLS en todas las tablas con `ALTER TABLE <tabla> ENABLE ROW LEVEL SECURITY`. Añade una política permisiva para `service_role` en todas las tablas (para que el backend pueda operar sin restricciones). Las políticas adicionales de usuario son las descritas en §6.2 de este documento.

```sql
-- Política base para service_role (backend) en cada tabla
CREATE POLICY "service_role_all" ON providers
  FOR ALL USING (auth.role() = 'service_role');
-- Repetir para tasks, wallets, task_assignments, transactions
```

**Paso 3 — Verificar índices**

Los siguientes índices son críticos para el rendimiento:
- `idx_task_assignments_provider_id` en `task_assignments(provider_id)`
- `idx_task_assignments_status` en `task_assignments(status)`
- `idx_transactions_provider_created` en `transactions(provider_id, created_at DESC)`
- `idx_tasks_status_slots` en `tasks(status, slots_left)` (para el listado de tareas disponibles)

**Paso 4 — Confirmar valores iniciales**

La columna `accuracy` en `providers` debe tener `DEFAULT 80.00` (no `0.00`).
La columna `response_time_score` en `providers` debe tener `DEFAULT 70.00`.
La columna `client_rating` en `providers` debe tener `DEFAULT 70.00`.
La columna `is_online` en `providers` debe tener `DEFAULT false`.
La columna `rank` en `providers` debe tener `DEFAULT 'nuevo'`.

**Paso 5 — Copiar las Connection Strings**

Del panel Supabase (Settings → Database → Connection string):
- **Direct connection** (puerto 5432): para migraciones futuras
- **Pooler connection** (puerto 6543): para el backend del MVP (`SUPABASE_DB_URL`)

Proporcionarlas al Backend Dev para rellenar `.env`.

### Resumen del modelo de datos para el Database Engineer

```
providers (1)────────────(1) wallets
     │                          │
     │                          └── available_balance, pending_balance,
     │                               total_earned, total_withdrawn
     │
     ├────────(N) task_assignments (N)──────(1) tasks
     │              │                              │
     │              └── status, reward_paid,       └── stages[], slots_left,
     │                   trust_delta, started_at        duration_min/max
     │
     └────────(N) transactions
                    │
                    ├── tx_type: pago_tarea | retiro | bonus | penalizacion
                    └── (FK nullable) task_id
```

El campo `stages` en `tasks` es de tipo `text[]` (array de PostgreSQL). El seed debe poblar este campo con arrays de 4-6 strings descriptivos por tarea.

El campo `rank` usa valores en español con acento: `'nuevo'`, `'confiable'`, `'experto'`, `'elite'` (sin acento en "elite" para evitar problemas de encoding en comparaciones). La UI muestra "Élite" con acento, pero la BD almacena `'elite'`.

---

## 12. Pipeline de Cómputo Distribuido

### 12.1 Diagrama de flujo completo

```
CLIENTE (proveedor con rol cliente)
        │
        │ POST /jobs  (CSV + params)
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│  compute_service.create_job()                                         │
│                                                                       │
│  1. Valida job_type y params                                          │
│  2. Persiste job con status='pending'   [compute_queries]            │
│  3. Lee CSV → divide en chunks de ~500 filas                          │
│  4. Persiste N chunks con status='pending'  [compute_queries]        │
│  5. Actualiza job: status='processing', total_chunks=N               │
│  6. Devuelve JobPublic al cliente                                      │
└───────────────────────────────────────────────────────────────────────┘
        │
        │  (job en BD con N chunks status=pending)
        │
        ▼ (polling de N workers simultáneos)
┌───────────────────────────────────────────────────────────────────────┐
│  WORKER A                        WORKER B                             │
│                                                                       │
│  POST /work/claim                POST /work/claim                     │
│  ┌─────────────────────────┐     ┌─────────────────────────┐         │
│  │ psycopg2 BEGIN          │     │ psycopg2 BEGIN          │         │
│  │ UPDATE chunks           │     │ UPDATE chunks           │         │
│  │   WHERE status=pending  │     │   WHERE status=pending  │         │
│  │   FOR UPDATE SKIP LOCKED│     │   FOR UPDATE SKIP LOCKED│         │
│  │   SET status=assigned   │     │   SET status=assigned   │         │
│  │   RETURNING ...         │     │   RETURNING ...         │         │
│  │ COMMIT                  │     │ COMMIT                  │         │
│  └─────────────────────────┘     └─────────────────────────┘         │
│         │ chunk[0]                       │ chunk[0] (réplica 2)      │
│         ▼                               ▼                            │
│  plugin.process(payload)        plugin.process(payload)              │
│  (polars: mean/sum/etc.)        (polars: mean/sum/etc.)              │
│         │ result_A                       │ result_B                  │
│         ▼                               ▼                            │
│  POST /work/{chunk_id}/submit   POST /work/{chunk_id}/submit         │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│  consensus_service.evaluate_chunk()                                   │
│                                                                       │
│  Al recibir cada submit:                                              │
│  1. Persiste chunk_result (is_valid=null)                             │
│  2. Cuenta resultados en chunk_results para ese chunk_id              │
│                                                                       │
│  Con 2 resultados (replicas_needed=2):                                │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  canonical_A = json.dumps(result_A, sort_keys=True)         │     │
│  │  canonical_B = json.dumps(result_B, sort_keys=True)         │     │
│  │                                                             │     │
│  │  if canonical_A == canonical_B:                             │     │
│  │      → ambos is_valid=True                                  │     │
│  │      → chunk.status = 'done'                                │     │
│  │      → job.completed_chunks += 1 (atómico)                  │     │
│  │      → pagar a A y B (wallet_service)                       │     │
│  │      → actualizar trust A y B (accuracy +2)                 │     │
│  │  else:                                                       │     │
│  │      → chunk.status = 'pending' (vuelve a la cola)          │     │
│  │      → asignar 3.er worker para desempate                   │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  Con 3 resultados (desempate):                                        │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  Mayoría (2 de 3 coinciden):                                │     │
│  │      → los 2 coincidentes: is_valid=True, pago + accuracy+2 │     │
│  │      → el discrepante: is_valid=False, accuracy-5           │     │
│  │      → chunk.status = 'done'                                │     │
│  │      → job.completed_chunks += 1 (atómico)                  │     │
│  │  Sin mayoría (3 resultados distintos):                       │     │
│  │      → todos is_valid=False, accuracy-5 a los 3             │     │
│  │      → chunk.status = 'rejected'                            │     │
│  └─────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
        │
        │ Cuando completed_chunks == total_chunks
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│  compute_service.finalize_job()                                       │
│                                                                       │
│  1. Consolida resultados válidos de todos los chunks (reduce)         │
│  2. Persiste job.result (jsonb consolidado)                           │
│  3. Actualiza job: status='completed', completed_at=now()             │
│  4. Cliente puede llamar GET /jobs/{id}/result                        │
└───────────────────────────────────────────────────────────────────────┘
```

---

### 12.2 Estructura de directorios nueva

Los directorios y módulos que los desarrolladores deben crear (sin tocar los existentes):

```
backend/app/
│
├── routers/
│   ├── compute.py          # Router /jobs: POST /jobs, GET /jobs,
│   │                       #   GET /jobs/{job_id}, GET /jobs/{job_id}/result
│   │                       #   Prefijo registrado en main.py: "/jobs"
│   │                       #   Tags: ["compute"]
│   └── work.py             # Router /work: POST /work/claim,
│                           #   POST /work/{chunk_id}/submit
│                           #   Prefijo registrado en main.py: "/work"
│                           #   Tags: ["work"]
│
├── services/
│   ├── compute_service.py  # create_job(client_id, job_type, params, csv_data)
│   │                       #   → Orquesta: validar, split, persistir chunks
│   │                       # get_job(job_id, client_id) → JobPublic
│   │                       # list_jobs(client_id, status_filter) → list[JobPublic]
│   │                       # get_job_result(job_id, client_id) → dict
│   │                       # finalize_job(job_id) → llamado internamente por consensus
│   │                       #   → reduce parciales, persist result, status=completed
│   │                       # split_csv(csv_bytes, chunk_size=500) → list[dict]
│   │                       #   → pura, no accede a BD
│   │
│   └── consensus_service.py  # evaluate_chunk(chunk_id, provider_id, result, duration_ms)
│                              #   → Persiste chunk_result
│                              #   → Cuenta réplicas entregadas
│                              #   → Compara con json.dumps(sort_keys=True)
│                              #   → Llama wallet_service y trust_score según consenso
│                              #   → Si job completo, llama compute_service.finalize_job
│                              #   Retorna SubmitResponse
│
├── db/
│   └── queries/
│       └── compute_queries.py  # create_job(client_id, job_type, params) → dict
│                               # update_job_status(job_id, status) → dict
│                               # update_job_chunks_count(job_id, total) → dict
│                               # increment_completed_chunks(job_id) → int (atómico)
│                               # set_job_result(job_id, result) → dict
│                               # get_job_by_id(job_id) → dict | None
│                               # get_jobs_by_client(client_id, status_filter) → list[dict]
│                               # create_chunk(job_id, chunk_index, payload) → dict
│                               # claim_chunks_atomic(provider_id, max_chunks) → list[dict]
│                               #   → USA psycopg2 con BEGIN/FOR UPDATE SKIP LOCKED/COMMIT
│                               #   → NO usa el SDK de Supabase (no garantiza atomicidad)
│                               # get_chunk_by_id(chunk_id) → dict | None
│                               # update_chunk_status(chunk_id, status, assigned_to) → dict
│                               # create_chunk_result(chunk_id, provider_id, result, duration_ms)
│                               # get_chunk_results(chunk_id) → list[dict]
│                               # update_chunk_result_validity(result_id, is_valid) → dict
│                               # get_valid_results_for_job(job_id) → list[dict]
│
└── worker/
    ├── __init__.py
    ├── main.py             # Entry point: python -m app.worker
    │                       #   CLI: --api, --email, --password, --poll-interval
    │                       #   1. POST /auth/login → obtiene JWT
    │                       #   2. Loop: POST /work/claim → procesa → POST /work/{id}/submit
    │                       #   3. Sleep(poll_interval) si chunks=[] (backoff exponencial)
    │                       #   Lanza N instancias en paralelo con asyncio o threading
    │                       #   Script de demo: scripts/run_workers.sh (lanza 3 workers)
    │
    └── plugins/
        ├── __init__.py     # Registro de plugins: PLUGINS = {"data-processing": DataProcessingPlugin}
        ├── base.py         # Clase abstracta WorkerPlugin:
        │                   #   process(payload: dict) -> dict  [abstractmethod]
        │                   #   job_type: str                   [class attribute]
        └── data_processing.py  # DataProcessingPlugin(WorkerPlugin)
                            #   job_type = "data-processing"
                            #   process(payload):
                            #     import polars as pl
                            #     df = pl.DataFrame({"col": rows})
                            #     Aplica params["operation"]: mean/sum/min/max/count
                            #     Retorna {"<col>_<operation>": valor, ...}
```

**Registro de routers en `app/main.py` (2 líneas a añadir):**

```python
from app.routers import compute, work           # añadir al import existente

app.include_router(compute.router, prefix="/jobs",  tags=["compute"])
app.include_router(work.router,    prefix="/work",  tags=["work"])
```

---

### 12.3 Claim atómico con psycopg2

El claim de chunks es la operación más crítica del sistema: si no es atómica, dos workers pueden procesar el mismo chunk asignado al mismo proveedor, desperdiciando cómputo o corrompiendo el consenso.

**Implementación en `compute_queries.claim_chunks_atomic`:**

```python
import psycopg2
from app.core.config import settings

def claim_chunks_atomic(provider_id: str, max_chunks: int) -> list[dict]:
    """
    Reclama hasta max_chunks chunks pendientes para provider_id de forma atómica.
    Usa psycopg2 directo (no SDK Supabase) para garantizar FOR UPDATE SKIP LOCKED.
    """
    conn = psycopg2.connect(settings.supabase_db_url)
    try:
        with conn:           # BEGIN implícito; COMMIT en __exit__ si no hay excepción
            with conn.cursor() as cur:
                cur.execute("""
                    WITH candidates AS (
                        SELECT c.id
                        FROM chunks c
                        WHERE c.status = 'pending'
                          AND NOT EXISTS (
                              SELECT 1 FROM chunk_results cr
                              WHERE cr.chunk_id = c.id
                                AND cr.provider_id = %(provider_id)s
                          )
                        ORDER BY c.created_at ASC
                        LIMIT %(max_chunks)s
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE chunks
                    SET status      = 'assigned',
                        assigned_to = %(provider_id)s,
                        attempts    = attempts + 1
                    FROM candidates
                    WHERE chunks.id = candidates.id
                    RETURNING
                        chunks.id          AS chunk_id,
                        chunks.job_id,
                        chunks.chunk_index,
                        chunks.payload,
                        chunks.replicas_needed
                """, {"provider_id": provider_id, "max_chunks": max_chunks})
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()
```

**Por qué no se usa el SDK de Supabase aquí:** El SDK de Supabase Python no expone `FOR UPDATE SKIP LOCKED`. Sin este hint, PostgreSQL bloquea las filas candidatas mientras las evalúa, causando que workers concurrentes esperen en lugar de saltar a la siguiente fila disponible. Con psycopg2 y `SKIP LOCKED`, cada worker obtiene instantáneamente sus propios chunks sin espera ni duplicados.

**Conexión de psycopg2:** Usa `SUPABASE_DB_URL` (puerto 6543, pooler), la misma variable ya definida en `app/core/config.py`. No se añade ninguna variable de entorno nueva.

---

### 12.4 Lógica de consenso

Implementada en `consensus_service.evaluate_chunk`. La comparación de resultados es **canónica**: se serializa cada resultado JSON con `json.dumps(result, sort_keys=True)` antes de comparar strings, garantizando que `{"a":1,"b":2}` y `{"b":2,"a":1}` se traten como idénticos.

**Flujo de `evaluate_chunk(chunk_id, provider_id, result, duration_ms)`:**

```
1. Verificar que chunk existe y está en status='assigned'
   └── Si no → HTTPException 400

2. Verificar que el proveedor tiene este chunk asignado (assigned_to == provider_id)
   └── Si no → HTTPException 400 "No tienes este chunk asignado"

3. Verificar que el proveedor no ha entregado ya un resultado
   └── Si ya existe chunk_results(chunk_id, provider_id) → HTTPException 400

4. Persistir chunk_result con is_valid=null

5. Cargar TODOS los chunk_results para este chunk_id

6. Si len(resultados) < replicas_needed:
   └── Devolver SubmitResponse(status='assigned', message='Esperando réplica...')

7. Si len(resultados) == 2 (caso normal, replicas_needed=2):
   canonical = [json.dumps(r["result"], sort_keys=True) for r in resultados]
   ┌── SI canonical[0] == canonical[1]:
   │       → update is_valid=True en ambos
   │       → update chunk.status = 'done'
   │       → increment_completed_chunks(job_id)  [UPDATE jobs SET completed_chunks = completed_chunks+1 WHERE ...]
   │       → pagar reward_per_chunk a cada proveedor (wallet_service.credit_reward)
   │       → update accuracy +2 a cada proveedor (trust_score.update_accuracy_on_complete)
   │       → recalcular trust_score y rank de cada proveedor
   │       → Si completed_chunks == total_chunks → compute_service.finalize_job(job_id)
   │       → Devolver SubmitResponse(status='done')
   └── SI NO coinciden:
           → chunk.status = 'pending', assigned_to = null  (vuelve a cola)
           → El siguiente POST /work/claim puede asignarlo a un 3.er worker
           → Devolver SubmitResponse(status='assigned', message='Desacuerdo...')

8. Si len(resultados) == 3 (ronda de desempate):
   canonicals = [json.dumps(r["result"], sort_keys=True) for r in resultados]
   groups = Counter(canonicals)
   majority_canonical, majority_count = groups.most_common(1)[0]
   ┌── SI majority_count >= 2:
   │       → los que coinciden con majority: is_valid=True, pago + accuracy+2
   │       → los que discrepan: is_valid=False, accuracy-5
   │       → chunk.status = 'done'
   │       → increment_completed_chunks, finalize si procede
   └── SI majority_count == 1 (3 distintos):
           → todos is_valid=False, accuracy-5 a los 3
           → chunk.status = 'rejected'
           → NO se incrementa completed_chunks
           → job puede quedar en estado 'failed' si demasiados chunks rejected
             (política: si rejected_chunks > total_chunks * 0.5 → job.status='failed')
```

---

### 12.5 Integración con servicios existentes

El pipeline de cómputo reutiliza sin modificar los servicios existentes:

**`wallet_service` (`app/services/wallet_service.py`):**

Se necesita una función adicional `credit_reward(provider_id, amount, description)` que acredite saldo directamente (el flujo inverso al retiro). Esta función NO existe actualmente y debe añadirse al servicio. Contrato esperado:

```python
def credit_reward(provider_id: str, amount: float, description: str) -> None:
    """
    Acredita amount en wallets.available_balance y total_earned del proveedor.
    Crea transaction(tx_type='pago_tarea', status='completada').
    """
```

`consensus_service` la llama por cada proveedor con resultado válido al cerrar un chunk.

**`trust_score` (`app/services/trust_score.py`):**

Se invocan directamente las funciones puras existentes:
- `update_accuracy_on_complete(current_accuracy)` — resultado válido
- `update_accuracy_on_fail(current_accuracy)` — resultado inválido
- `calculate_trust_score(completion_rate, accuracy, response_time_score, client_rating)` — recalcular
- `get_rank(trust_score)` — nuevo rango

`response_time_score` no cambia con los eventos de chunk (la fórmula de `response_time` está vinculada al tiempo de aceptación de task, no al tiempo de procesamiento de chunks). `completion_rate` tampoco cambia (es métrica de tasks, no de jobs).

**`auth` / `get_current_provider` (`app/core/dependencies.py`):**

Los routers `compute.py` y `work.py` usan exactamente la misma dependencia `Depends(get_current_provider)` que los routers existentes. El worker se autentica con `POST /auth/login` reusando el endpoint existente.

---

### 12.6 Estrategia de splitting para CSV (data-processing)

El splitting es una función pura en `compute_service.split_csv`:

```
Entrada: csv_bytes (bytes), params (dict), chunk_size=500

1. Decodificar bytes → string UTF-8
2. csv.reader → extraer headers (primera fila)
3. Leer todas las filas de datos
4. Dividir en grupos de chunk_size filas
5. Para cada grupo[i]:
   payload = {
     "rows": group[i],        # list of lists
     "columns": headers,      # list of strings
     "operation": params["operation"],
     "target_columns": params.get("columns", headers)  # columnas a operar
   }
6. Retornar list[payload]
```

El payload de cada chunk contiene solo las filas necesarias más los metadatos de operación. El worker no necesita conocer el job completo para procesar su chunk.

**Límite de tamaño:** 10 MB de CSV ≈ ~500.000 filas típicas → ~1.000 chunks. Para el MVP se acepta hasta 10 MB. El router rechaza con 413 si `file.size > 10 * 1024 * 1024`.

---

### 12.7 Plugin del Worker

La interfaz de plugin en `app/worker/plugins/base.py`:

```python
from abc import ABC, abstractmethod

class WorkerPlugin(ABC):
    job_type: str  # class attribute, e.g. "data-processing"

    @abstractmethod
    def process(self, payload: dict) -> dict:
        """
        Procesa un chunk y retorna el resultado.
        payload: {"rows": [...], "columns": [...], "operation": "mean", "target_columns": [...]}
        Retorna: {"<col>_<operation>": value, ...} para data-processing
        """
```

`DataProcessingPlugin` implementa `process` usando polars:

```python
import polars as pl

class DataProcessingPlugin(WorkerPlugin):
    job_type = "data-processing"

    def process(self, payload: dict) -> dict:
        df = pl.DataFrame(
            data=payload["rows"],
            schema=payload["columns"],
            orient="row"
        )
        target_cols = payload.get("target_columns", payload["columns"])
        operation = payload["operation"]
        result = {}
        for col in target_cols:
            if col not in df.columns:
                continue
            series = df[col].cast(pl.Float64, strict=False).drop_nulls()
            if operation == "mean":   result[f"{col}_mean"]  = series.mean()
            elif operation == "sum":  result[f"{col}_sum"]   = series.sum()
            elif operation == "min":  result[f"{col}_min"]   = series.min()
            elif operation == "max":  result[f"{col}_max"]   = series.max()
            elif operation == "count":result[f"{col}_count"] = series.len()
        return result
```

Añadir futuros tipos de job (e.g. `transcription`) requiere solo:
1. Crear `app/worker/plugins/transcription.py` con la clase correspondiente.
2. Registrar en `app/worker/plugins/__init__.py`.
3. Añadir el literal al CHECK de `jobs.job_type` en una nueva migración SQL.

---

### 12.8 Seguridad — Nota de riesgo documentado

**RIESGO: el worker ejecuta codigo del servidor sin sandboxing.**

El worker Python (`app/worker/main.py`) descarga payloads de la API y los procesa directamente con polars en el proceso del worker. Si la API fuese comprometida o un payload malicioso fuese inyectado en la base de datos, podría ejecutarse código arbitrario en la máquina del worker.

**Mitigaciones en el MVP (parciales):**
- El payload solo contiene datos tabulares (listas de listas); no contiene código ejecutable.
- El plugin `DataProcessingPlugin.process` no usa `eval`, `exec` ni deserialización de objetos arbitrarios.
- La comunicación worker ↔ API es HTTPS con JWT.

**Fuera del alcance del MVP:**
- Sandboxing real (contenedor Docker aislado con seccomp/AppArmor).
- Verificación de integridad del payload (firma HMAC).
- Ejecución en entorno restricto (sin acceso a red, filesystem limitado).

Esta limitación debe documentarse en el README del worker con un aviso explícito antes del despliegue en producción.

---

### 12.9 Tests del pipeline de cómputo

Los tests de integración del pipeline deben cubrir el flujo end-to-end sin mocking de BD. Se ubican en `backend/tests/test_compute.py` y `backend/tests/test_consensus.py`.

**Casos obligatorios para `test_compute.py`:**

| ID | Descripción |
|----|-------------|
| C-01 | `POST /jobs` con CSV de 1200 filas → job con 3 chunks, status=processing |
| C-02 | `GET /jobs` lista solo los jobs del proveedor autenticado |
| C-03 | `GET /jobs/{id}` progreso = `completed_chunks / total_chunks * 100` |
| C-04 | `GET /jobs/{id}/result` devuelve 400 si job no está completed |
| C-05 | `POST /jobs` con CSV vacío → 400 |

**Casos obligatorios para `test_consensus.py`:**

| ID | Descripción |
|----|-------------|
| K-01 | Dos workers envían el mismo resultado → ambos is_valid=True, chunk=done, job.completed_chunks+=1 |
| K-02 | Dos workers envían resultados distintos → chunk vuelve a pending para 3.er worker |
| K-03 | 3.er worker desempata con la mayoría → mayoría is_valid=True, disidente is_valid=False |
| K-04 | 3 resultados distintos → todos is_valid=False, chunk=rejected |
| K-05 | Último chunk validado → finalize_job ejecutado, job.status=completed |
| K-06 | Worker intenta enviar resultado de chunk no asignado → 400 |
| K-07 | Worker intenta enviar resultado duplicado → 400 |

**Fixtures necesarias en `tests/conftest.py` (añadir sin modificar las existentes):**

```python
@pytest.fixture
def mock_job():
    return {
        "id": "job-uuid-test",
        "client_id": "550e8400-...",
        "job_type": "data-processing",
        "status": "processing",
        "total_chunks": 2,
        "completed_chunks": 0,
        "reward_total": 0.20,
        ...
    }

@pytest.fixture
def mock_chunk():
    return {
        "id": "chunk-uuid-test",
        "job_id": "job-uuid-test",
        "chunk_index": 0,
        "status": "assigned",
        "assigned_to": "550e8400-...",
        ...
    }
```

---

### 12.10 Handoff para el Database Engineer — Compute

Las tablas `jobs`, `chunks` y `chunk_results` ya están creadas por la migración `migrations/004_compute.sql`. Las acciones requeridas son:

**Paso 1 — Ejecutar `migrations/004_compute.sql`** en el SQL Editor de Supabase (si no se ha hecho ya).

El fichero es idempotente (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `DROP POLICY IF EXISTS`).

**Paso 2 — Verificar índices críticos** para el rendimiento del claim atómico:

- `idx_chunks_status` en `chunks(status)` — consulta masiva de chunks pendientes
- `idx_chunks_job_status` en `chunks(job_id, status)` — conteo de chunks por job
- `idx_chunk_results_chunk_id` en `chunk_results(chunk_id)` — validación de consenso
- `idx_chunk_results_is_valid` en `chunk_results(chunk_id, is_valid)` — consolidación

**Paso 3 — Confirmar restricciones CHECK** en `jobs.job_type`:

El check actual es `CHECK (job_type IN ('data-processing'))`. Cuando se añadan nuevos tipos, se ejecutará una migración adicional `ALTER TABLE jobs DROP CONSTRAINT jobs_job_type_values; ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_values CHECK (job_type IN ('data-processing', 'transcription'));`.

**Paso 4 — RLS:** Las políticas `service_role_all` ya están en la migración. No añadir restricciones adicionales hasta migrar a Supabase Auth (ver §6.3 de este documento).

**Modelo de datos nuevo (diagrama):**

```
providers (1) ─────────────────── (N) jobs
     │                                  │
     │   assigned_to (nullable)         │
     └── (N) chunks ────────────────────┘  (job_id)
              │
              └── (N) chunk_results
                          │
                          └── provider_id → providers (1)
```

---

## 13. Ampliación — Botón "Añadir Créditos" (Placeholder) y Verificación de Despliegue

Esta sección responde al encargo de `briefs/05-vercel-creditos.md` (ver `docs/02-backlog.md`, US-42 y CH-01).

### 13.1 US-42 — Botón "Añadir créditos": sin cambios de arquitectura

El botón "Añadir créditos" de `WalletPage.tsx` es UI pura: al pulsarlo abre el componente `Modal` ya existente (`components/ui/Modal.tsx`) con un mensaje estático de "función en construcción" y una acción para cerrarlo. No dispara ninguna llamada HTTP, no introduce estado nuevo, no requiere ningún endpoint ni router nuevo, no modifica el modelo de datos y no toca ningún contrato de `docs/04-api-contracts.md`. **Backend Dev y Database Engineer no tienen ninguna tarea derivada de esta historia**: no hay endpoint que implementar ni tabla ni columna que crear o migrar. Es explícitamente distinto del flujo real de recarga del cliente (`POST /client/deposit`, brief 03), que esta historia no toca ni duplica.

### 13.2 CH-01 — Verificación de despliegue: sin cambios de arquitectura

La arquitectura de despliegue (SPA estática en Vercel + API FastAPI en Railway + Supabase Cloud, CORS restringido a `FRONTEND_URL`, `ENVIRONMENT=production` desactivando `/docs` y `/redoc`) quedó fijada en el brief `04-deploy-landing.md` y no cambia con esta ampliación. La verificación de que `DEPLOY.md` y `frontend/vercel.json` siguen reflejando el estado actual del código es un chore de revisión (propiedad de DevOps) y no introduce servicios, capas ni patrones nuevos. No hay nada bloqueante para autorizar la publicación desde el punto de vista de la arquitectura.

### 13.3 Corrección menor detectada durante esta revisión

Al releer este documento y `docs/04-estructura.md` para confirmar lo anterior, se detectó que ninguno de los dos reflejaba todavía la estructura de la feature "Lado Cliente" (brief 03), ya implementada en código: router `app/routers/client.py` (prefijo `/client`), `app/services/client_service.py`, `app/db/queries/client_queries.py`, la tabla `escrows` y la columna `tasks.client_id` (`migrations/005_client.sql`), y las pantallas `frontend/src/pages/client/*`. El diagrama de §1 y el listado de tablas de §11 de este documento describen el MVP original y, al igual que ocurrió con la feature de cómputo (§12, que tampoco se retroalimentó a §1), quedaron desactualizados antes de esta ampliación; no es un problema introducido por `briefs/05-vercel-creditos.md` ni bloquea el despliegue. Se añade una sección breve en `docs/04-estructura.md` ("Estructura adicional — Feature Lado Cliente") para dejar constancia mínima de estos ficheros, siguiendo el mismo patrón aditivo ya usado para cómputo, sin reescribir el diagrama ni el §11. No se añaden endpoints nuevos a `docs/04-api-contracts.md`: documentar formalmente los contratos de `/client` y `/client/deposit` queda fuera del alcance de esta ampliación.

---

## 14. Estabilidad v3 — TTL de Chunks Asignados y Transaccionalidad de Pago + Trust

**Fecha:** 2026-07-07
**Autor:** Software Architect
**Referencias:** `docs/07-entrega.md` ("Próximos pasos sugeridos para v3", puntos 1 y 3), `docs/05-review.md` (R2-C-03, R2-A-04, R2-A-06, R3-CRIT-02)

Esta sección diseña la corrección de las dos primeras correcciones de fiabilidad priorizadas por el Product Owner para v3: (1) chunks que quedan atascados en `assigned` sin TTL, y (2) el pago y la actualización de trust score en `consensus_service._pay_and_update_trust` no son transaccionales. No es un brief formal — es una iniciativa de estabilidad sobre deuda ya identificada. Esta sección es aditiva; no modifica el §12 (Pipeline de Cómputo Distribuido), que sigue describiendo el diseño original — donde este documento lo actualiza, se indica explícitamente.

### 14.0 Verificación del estado real del código (previa al diseño)

Antes de diseñar se releyó el código actual (no solo los documentos de encargo). Hallazgos relevantes que matizan el encargo original:

1. **`migrations/004_compute.sql` (tabla `chunks`, líneas 91–116):** confirmado — existen `status`, `assigned_to`, `attempts` (default 0), `created_at`, pero ninguna columna de timestamp de asignación. Confirma el Problema 1 tal como está descrito.

2. **`compute_queries.claim_chunks_atomic` ya implementa el rechazo automático por `attempts >= 5`** (constante `MAX_CHUNK_ATTEMPTS = 5`, CTE `overdue`/`_reject`). Esto **no coincide** con `docs/07-entrega.md` punto 3 ("no implementado") ni con R2-A-04 — el código ha avanzado desde que se escribieron esos documentos. Sin embargo, esta lógica solo actúa sobre chunks en `status = 'pending'`, y **hoy no existe ningún camino que devuelva un chunk de `assigned` a `pending` salvo el propio flujo de consenso** (desacuerdo entre 2 réplicas, o esperando 2ª réplica — ambos en `consensus_service.py`, vía `update_chunk_status(chunk_id, "pending")`). Es decir: el rechazo por intentos está implementado pero es **casi inalcanzable en la práctica**, porque sin TTL casi ningún chunk vuelve a `pending` tras quedar `assigned` con un worker caído. El diseño de esta sección activa esta lógica ya existente en vez de duplicarla (ver §14.2.5).

3. **`consensus_service._pay_and_update_trust` (líneas 43–85) confirmado no transaccional**, y además el `except Exception` final (línea 78) **silencia el error** (solo `logger.error`, no reraise) — más grave que "no transaccional a secas": hoy, si falla la actualización de trust, ni siquiera hay señal de que el flujo quedó a medias más allá del log. Confirma el Problema 2.

4. **`wallet_queries.update_wallet_on_task_complete` confirmado atómico** (`UPDATE ... SET x = x + %s ... RETURNING *`, psycopg2, sin doble lectura) — el punto 2 de "próximos pasos v3" ya está resuelto. Esta función es compartida: además de usarla `wallet_service.credit_reward` (camino de cómputo), la usa directamente `task_lifecycle.py` línea 144 (camino de tareas clásicas). **No se modifica** — el diseño de esta sección añade una función nueva en paralelo, no toca esta.

5. **`get_provider_by_id`/`update_provider` confirmados en `auth_queries.py`/`profile_queries.py` respectivamente**, vía cliente REST de Supabase (`get_supabase().table("providers")...`). `consensus_service.py` importa `get_provider_by_id` de `auth_queries` y `update_provider` de `profile_queries`.

6. **`settings.supabase_db_url` confirmado obligatorio** (`backend/app/core/config.py` línea 9: `supabase_db_url: str`, sin `Optional`) y **`backend/app/db/supabase_client.py` confirmado ausente** del árbol de trabajo actual. El WIP descrito en `docs/05-review.md` (sección 2026-07-06, R3-CRIT-01/R3-CRIT-02) que debilitaba esta variable a opcional **no está presente hoy**. Ambos diseños de esta sección dependen de que seguirá siendo obligatoria — ver riesgo en §14.4.

7. **Ningún test actual (`test_compute.py`, `test_consensus.py`) mockea `psycopg2` ni testea `claim_chunks_atomic` o `/work/claim`** — los tests K-01…K-07 cubren `process_chunk_submission` (envío), no el claim. Esto reduce el riesgo de romper tests existentes al modificar el claim, pero también significa que hoy no hay cobertura de regresión sobre él (nota para QA en §14.7).

---

### 14.2 Problema 1 — TTL de chunks asignados (reclamo perezoso)

#### 14.2.1 Mecanismo elegido

**Reclamo perezoso dentro del propio `POST /work/claim`, sin scheduler.** Se confirma la intuición del encargo: es la opción correcta dado el stack real (FastAPI + Uvicorn `--workers 2`, sin APScheduler/Celery/RQ en `requirements.txt`, confirmado por grep). Los workers ya hacen polling a `/work/claim` cada 5s cuando no hay trabajo (`backend/app/worker/main.py`, `--interval 5` por defecto), lo que garantiza que ningún chunk expirado espera más de lo que tarde el siguiente poll de **cualquier** worker activo en recibir tratamiento — y si no hay ningún worker activo, no hay urgencia real de reclamar (nadie está esperando para procesar).

**Alternativas consideradas y descartadas:**

- **APScheduler en el propio proceso:** añadiría una dependencia nueva y, con `--workers 2`, cada proceso Uvicorn correría su propio scheduler in-memory de forma redundante (dos jobs periódicos idénticos sin coordinación) — no hay forma barata de garantizar "solo uno de los dos procesos ejecuta el cleanup" sin añadir además un lock distribuido. El beneficio (limpieza sin depender de que llegue una request) no compensa la complejidad, dado que el polling ya cubre el caso con creces.
- **`pg_cron` en Supabase:** técnicamente viable (Supabase soporta la extensión), pero añade una dependencia operativa nueva (activar la extensión, mantener el job SQL fuera del código versionado del backend) para un beneficio ya cubierto por el patrón de polling existente. Se descarta por simplicidad; revisar solo si el proyecto elimina el polling (p. ej. al migrar a un modelo push/WebSocket para workers).
- **TTL a nivel de aplicación con hilo en background (`threading.Timer` o similar dentro de FastAPI):** mismo problema de duplicación entre los 2 workers de Uvicorn que APScheduler, sin ninguna ventaja sobre el reclamo perezoso.

**Umbral:** 10 minutos, tal como sugiere `docs/07-entrega.md`. Se fija como constante de módulo (no variable de entorno), siguiendo el mismo patrón que la constante ya existente `MAX_CHUNK_ATTEMPTS = 5` en `compute_queries.py`.

#### 14.2.2 Cambio de esquema: columna `chunks.assigned_at`

Nueva columna **`assigned_at timestamptz NULL`** en `chunks`.

**Regla de invariante (para que el TTL sea correcto y para que la tabla sea legible en inspección manual): `assigned_at` es NOT NULL si y solo si `status = 'assigned'`.**

- **Se pone a `now()`** exclusivamente en el UPDATE de `claim_chunks_atomic` que transiciona un chunk a `assigned` (§14.2.4, sentencia 3).
- **Se pone a `NULL`** en cualquier transición que saque un chunk de `assigned` — lo que incluye el reclamo por TTL (§14.2.4, sentencia 1) y las transiciones ya existentes en `consensus_service.py` vía `compute_queries.update_chunk_status(chunk_id, status)` (esperando 2ª réplica, desacuerdo entre réplicas → vuelve a `pending`; consenso alcanzado → `done`; rechazo final → `rejected`). Esto requiere **modificar `update_chunk_status`** (hoy solo gestiona `assigned_to`) para que también limpie `assigned_at` cuando `status != 'assigned'`.

No se añade ninguna `CHECK` constraint sobre esta invariante (validarla en SQL requeriría un trigger; se considera innecesario para el alcance de v3 — la disciplina se mantiene a nivel de aplicación, igual que ya ocurre hoy con la relación `assigned_to`/`status`).

**Índice nuevo**, para que el filtro de reclamo (`status = 'assigned' AND assigned_at < ...`) no dependa de un full scan a medida que crece `chunks`:

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_assigned_at
    ON chunks (assigned_at)
    WHERE status = 'assigned';
```

#### 14.2.3 Migración

**Archivo nuevo: `migrations/006_chunk_ttl.sql`** (el siguiente número disponible; `005_client.sql` es la última migración existente). Idempotente, siguiendo la convención del proyecto:

```sql
-- =============================================================================
-- Co-Computing — Migration 006: TTL de asignación de chunks
-- PostgreSQL 15 (Supabase)
-- Ejecutar DESPUÉS de 001_schema.sql .. 005_client.sql
-- =============================================================================

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS assigned_at timestamptz;

COMMENT ON COLUMN chunks.assigned_at IS
    'Timestamp de la asignación vigente. NULL si status != assigned (invariante mantenida por la aplicación, no por constraint). Usado por el reclamo perezoso: un chunk assigned cuyo assigned_at supere el TTL (10 min, ver compute_queries.CHUNK_ASSIGNMENT_TTL_MINUTES) se devuelve a pending en la siguiente llamada a POST /work/claim.';

CREATE INDEX IF NOT EXISTS idx_chunks_assigned_at
    ON chunks (assigned_at)
    WHERE status = 'assigned';
```

No se requiere backfill: los chunks ya existentes en `assigned` (si los hay al desplegar) quedarán con `assigned_at IS NULL`, que la condición `assigned_at < now() - interval` nunca cumple (`NULL` no es menor que nada) — no serán reclamados automáticamente hasta su **próxima** asignación, que sí fijará `assigned_at`. Esto es aceptable para v3 (no deja nada en peor estado del que ya está) pero **el Database Engineer debe decidir si aplica un `UPDATE chunks SET status='pending', assigned_to=NULL WHERE status='assigned'` manual una sola vez, antes o durante el despliegue de esta migración**, para limpiar cualquier chunk ya atascado hoy en producción. Se deja como decisión operativa suya, no como parte del script idempotente (un `UPDATE` de limpieza puntual no debe repetirse en cada ejecución de la migración).

#### 14.2.4 `claim_chunks_atomic`: nueva secuencia de 3 sentencias

`compute_queries.claim_chunks_atomic` pasa de una única sentencia SQL a **tres sentencias secuenciales dentro de la misma conexión psycopg2 y la misma transacción** (un solo `conn.commit()` al final). Cambia su firma: **`claim_chunks_atomic(provider_id: str, max_chunks: int) -> tuple[list[dict], list[str]]`** — devuelve `(chunks_reclamados, job_ids_con_algun_chunk_rechazado)`.

**Por qué tres sentencias separadas y no todo fusionado en un único `WITH`:** PostgreSQL ejecuta todas las sub-sentencias de modificación de datos dentro de un mismo `WITH` **contra el mismo snapshot** tomado al inicio de esa sentencia — no pueden "verse" entre sí los cambios (esto es distinto de sentencias separadas dentro de la misma transacción, que sí ven los cambios de sentencias anteriores de la propia transacción). El código actual ya fusiona el rechazo por intentos (`overdue`/`_reject`) con el claim (`candidates`) en un único `WITH`, y **funciona correctamente hoy** solo porque los predicados son mutuamente excluyentes por construcción (`overdue` exige `attempts >= 5`, `candidates` exige `attempts < 5` — no importa que no se vean entre sí, nunca se solapan). Pero el paso de reclamo por TTL **si necesita** que su resultado (chunks que pasan a `pending`) sea visible para el paso de claim inmediatamente después, en la misma llamada — y eso **no se puede lograr fusionando todo en un único `WITH`**; si se intentara, el claim no vería los chunks recién reclamados hasta la siguiente llamada a `/work/claim` (que en la práctica también sería correcto, dado el polling cada 5s, pero es más frágil y sorprendente para quien mantenga este código después). La solución correcta y simple: tres `cur.execute()` separados sobre el mismo cursor/conexión, sin `commit()` entre medias — cada sentencia posterior ve los cambios (todavía no confirmados) de las anteriores porque pertenecen a la misma transacción.

```python
CHUNK_ASSIGNMENT_TTL_MINUTES = 10   # junto a MAX_CHUNK_ATTEMPTS = 5, mismo módulo

def claim_chunks_atomic(provider_id: str, max_chunks: int) -> tuple[list[dict], list[str]]:
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            # 1. RECLAMO — devuelve a pending los chunks 'assigned' cuyo TTL venció.
            #    No toca `attempts`: el intento ya se contó cuando se asignó;
            #    se cuenta de nuevo solo si se vuelve a asignar (sentencia 3).
            cur.execute("""
                UPDATE chunks
                SET status = 'pending',
                    assigned_to = NULL,
                    assigned_at = NULL
                WHERE status = 'assigned'
                  AND assigned_at < now() - make_interval(mins => %(ttl_minutes)s)
                RETURNING id AS chunk_id, job_id, attempts
            """, {"ttl_minutes": CHUNK_ASSIGNMENT_TTL_MINUTES})
            reclaimed = cur.fetchall()
            if reclaimed:
                logger.warning(
                    "TTL de asignación superado (%d min): %d chunk(s) devueltos a pending: %s",
                    CHUNK_ASSIGNMENT_TTL_MINUTES, len(reclaimed),
                    [str(r["chunk_id"]) for r in reclaimed],
                )

            # 2. RECHAZO POR INTENTOS — lógica YA EXISTENTE (MAX_CHUNK_ATTEMPTS=5),
            #    separada del claim (antes vivía en el mismo WITH); se añade RETURNING
            #    para poder disparar el cierre de job en la capa de servicio (§14.2.6).
            cur.execute("""
                WITH overdue AS (
                    SELECT id FROM chunks
                    WHERE status = 'pending' AND attempts >= %(max_attempts)s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE chunks SET status = 'rejected'
                FROM overdue
                WHERE chunks.id = overdue.id
                RETURNING chunks.id AS chunk_id, chunks.job_id AS job_id
            """, {"max_attempts": MAX_CHUNK_ATTEMPTS})
            rejected = cur.fetchall()

            # 3. CLAIM — lógica existente, sin cambios salvo `assigned_at = now()`.
            cur.execute("""
                WITH candidates AS (
                    SELECT c.id
                    FROM chunks c
                    WHERE c.status = 'pending'
                      AND c.attempts < %(max_attempts)s
                      AND NOT EXISTS (
                          SELECT 1 FROM chunk_results cr
                          WHERE cr.chunk_id = c.id
                            AND cr.provider_id = %(provider_id)s
                      )
                    ORDER BY c.created_at ASC
                    LIMIT %(max_chunks)s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE chunks
                SET status      = 'assigned',
                    assigned_to = %(provider_id)s,
                    assigned_at = now(),
                    attempts    = attempts + 1
                FROM candidates
                WHERE chunks.id = candidates.id
                RETURNING
                    chunks.id          AS chunk_id,
                    chunks.job_id,
                    chunks.chunk_index,
                    chunks.payload,
                    chunks.replicas_needed
            """, {
                "provider_id": provider_id,
                "max_chunks": max_chunks,
                "max_attempts": MAX_CHUNK_ATTEMPTS,
            })
            claimed = cur.fetchall()

            conn.commit()

    rejected_job_ids = list({str(r["job_id"]) for r in rejected})
    claimed_rows = [dict(r) for r in claimed]
    # ... enriquecimiento con job_type vía get_supabase(), sin cambios respecto al código actual ...
    return claimed_rows, rejected_job_ids
```

Nótese `make_interval(mins => %(ttl_minutes)s)` en vez de concatenar el número dentro de un literal `interval 'N minutes'`: permite parametrizar el TTL de forma segura con el mecanismo normal de psycopg2 (sin construir SQL por interpolación de strings), consistente con la regla ya documentada en este proyecto de "no interpolación de strings con datos" (aquí el dato es una constante interna, no input de usuario, pero se mantiene la misma disciplina).

**No se usa `SKIP LOCKED` en la sentencia 1 (reclamo):** a diferencia del claim (que necesita repartir chunks *distintos* entre workers concurrentes sin que se bloqueen entre sí), el reclamo no reparte nada — si dos llamadas a `/work/claim` concurrentes (los 2 procesos Uvicorn, por ejemplo) intentan reclamar el mismo chunk expirado, la segunda simplemente bloquea brevemente y al re-evaluar su `WHERE` tras el lock ya no encuentra la fila (el `status` ya cambió), afectando 0 filas — comportamiento estándar de `UPDATE` bajo `READ COMMITTED`, correcto sin necesitar `SKIP LOCKED`.

#### 14.2.5 Interacción con el rechazo automático por intentos (ya existente) y el cierre de job

Como se señaló en §14.0.2, el rechazo por `attempts >= 5` ya existe pero hoy es casi inalcanzable (nada devuelve `assigned → pending` salvo el propio consenso). Al añadir el reclamo por TTL, este mecanismo **se activa de verdad**: un chunk que se asigna, cuyo worker desaparece, se reclama (vuelve a `pending`, `attempts` sin tocar) y — si ya había acumulado `attempts >= 5` de asignaciones previas — la sentencia 2 de la **misma llamada** a `claim_chunks_atomic` lo rechaza inmediatamente (mismo transcurso de una única request HTTP `/work/claim`).

Esto expone una brecha preexistente que hoy es inofensiva por ser inalcanzable, pero que con el reclamo activo deja de serlo: **`claim_chunks_atomic` nunca ha llamado a `consensus_service._try_close_job`** tras rechazar un chunk. Si un job tiene todos sus chunks en estado terminal (`done`/`rejected`) pero el último en llegar a terminal lo hizo por esta vía (rechazo por intentos durante un claim, no durante un submit), **nadie vuelve a comprobar si el job debe cerrarse** — quedaría en `processing` para siempre, sustituyendo el síntoma original ("chunk atascado") por uno equivalente a nivel de job ("job atascado a pesar de que todos sus chunks ya son terminales"). Cerrar esta brecha es parte necesaria de esta corrección, no una ampliación de alcance: sin ella, el Problema 1 quedaría resuelto solo a medias.

La solución se documenta en §14.2.6: la capa de servicio, no `compute_queries`, es responsable de invocar `_try_close_job` para los job_ids devueltos como rechazados.

#### 14.2.6 Nueva capa de orquestación: `consensus_service.process_chunk_claim`

`_try_close_job` vive en `consensus_service.py` (capa de servicio) y no es una función pura — hace I/O (cuenta chunks, lee y actualiza el job, puede llamar a `compute_service.finalize_job`). Llamarla desde `compute_queries.py` (capa de repositorio) invertiría la dependencia de capas documentada en §2 de este mismo documento (Router → Service → Repository, nunca al revés). La solución correcta es que el router deje de llamar a `compute_queries.claim_chunks_atomic` directamente — hoy es la única operación de `/work` que salta la capa de servicio; `/work/{chunk_id}/submit` ya pasa correctamente por `consensus_service.process_chunk_submission` — y pase a llamar a una función de servicio nueva y simétrica:

```python
# app/services/consensus_service.py — función nueva

def process_chunk_claim(provider_id: str, max_chunks: int) -> list[dict]:
    """
    Punto de entrada de servicio para POST /work/claim.
    Reclama chunks para provider_id y, si el reclamo atómico rechazó chunks
    por exceso de intentos, revisa si alguno de esos jobs debe cerrarse.
    """
    claimed, rejected_job_ids = compute_queries.claim_chunks_atomic(provider_id, max_chunks)
    for job_id in rejected_job_ids:
        _try_close_job(job_id)
    return claimed
```

`_try_close_job` ya es idempotente (comprueba `job["status"] in ("completed", "failed")` y no hace nada si ya es terminal), así que no hay riesgo de doble-cierre si el submit y el claim lo invocan en ventanas solapadas.

**Cambio en `app/routers/work.py` (una línea):**

```python
# Antes:
rows = compute_queries.claim_chunks_atomic(provider_id, body.max_chunks)
# Después:
rows = consensus_service.process_chunk_claim(provider_id, body.max_chunks)
```

`work.py` ya importa `consensus_service` (se usa en `/submit`), así que no hace falta ningún import nuevo — solo **eliminar** el ahora-innecesario `from app.db.queries import compute_queries` (línea 13 actual; sin él, `work.py` no vuelve a referenciar `compute_queries` directamente en ningún otro punto).

---

### 14.3 Problema 2 — Transaccionalidad de pago + trust

#### 14.3.1 Enfoque elegido

Se confirma que el enfoque propuesto en el encargo es correcto y viable: **reescribir la actualización de trust para que use psycopg2 sobre `settings.supabase_db_url` y envolver crédito de wallet + registro de transacción + actualización de provider en una única transacción psycopg2.** No hay alternativa mejor dado el stack: el cliente REST de Supabase no expone transacciones multi-tabla, y psycopg2 directo contra `SUPABASE_DB_URL` ya es el mecanismo establecido en este proyecto para todo lo que necesita atomicidad real (`claim_chunks_atomic`, `update_wallet_on_task_complete`, `increment_job_completed_chunks`). Esta corrección sigue el mismo patrón, no introduce uno nuevo.

**Un añadido respecto al encargo original, de coste marginal dado que ya se reescribe esta ruta:** bloquear la fila del provider con `SELECT ... FOR UPDATE` dentro de la misma transacción antes de calcular los nuevos valores de trust. Sin este lock, dos chunks del mismo proveedor que alcanzan consenso de forma casi simultánea (realista con `replicas_needed=2`: dos workers entregando su segunda réplica casi a la vez para chunks distintos del mismo proveedor) podrían leer el mismo `accuracy`/`trust_score` de partida y perder una de las dos actualizaciones — el mismo patrón de carrera de lectura-modificación-escritura que ya se corrigió para `wallets` (C-03/R2-C-02), pero sin corregir todavía para `providers`. No estaba en el encargo original, pero es una consecuencia directa y barata de la misma reescritura — se documenta explícitamente como hallazgo de este diseño, no como ampliación de alcance no pedida.

**Excepción de capas, explícita y deliberada:** la nueva función vive en la capa de repositorio (`wallet_queries.py`) pero necesita invocar la lógica de cálculo de `app/services/trust_score.py` (fórmula de trust score, umbrales de rank, deltas de accuracy) para poder calcular los nuevos valores **mientras mantiene el lock de fila abierto** en la misma transacción — si el cálculo se hiciera fuera de la transacción (como hoy), se reabriría la misma ventana de carrera que se está cerrando. Se confirmó por grep que **ninguna función de `app/db/queries/*.py` importa hoy de `app/services/*`** — esta sería la primera. Se considera una excepción aceptable y acotada porque `trust_score.py` no tiene I/O ni dependencias de framework (solo `datetime`/`typing`), no depende a su vez de `app.db.queries` (cero riesgo de import circular), y la alternativa — mover la gestión de la transacción psycopg2 a la capa de servicio, con funciones de repositorio que reciban un cursor ya abierto en vez de gestionar su propia conexión — sería una desviación arquitectónica mayor (ningún servicio de este proyecto maneja psycopg2 directamente hoy; todas las funciones de `queries/*.py` son autocontenidas: abren su propia conexión, hacen su trabajo, la cierran). Entre las dos desviaciones posibles, importar una utilidad pura de cálculo es la más contenida. Se recomienda dejar un comentario en el código señalando explícitamente esta excepción para que no se generalice sin criterio.

**Qué se decide NO cambiar (para no ampliar el alcance):**

- **`task_lifecycle.py` (flujo de tareas clásicas) tiene el mismo patrón de fondo** (pago vía `wallet_queries.update_wallet_on_task_complete` en un paso, y `get_provider_by_id`/`update_provider` de `profile_queries` en otro, para el trust delta) — pero es un código y un flujo distintos de `consensus_service.py`, no mencionados en el encargo de esta iniciativa. **No se toca.** Se deja constancia aquí de que es un problema análogo pendiente, para una futura iteración.
- **El `except Exception` externo de `_pay_and_update_trust` se mantiene** (loguea con `exc_info=True` y no relanza) — no se cambia el comportamiento HTTP de `/work/{chunk_id}/submit` ante un fallo de este paso. Cambiar esto (propagar la excepción y devolver 500 al worker que hizo el submit, cuyo propio resultado ya se guardó correctamente) es una decisión de producto/contrato de API que excede "hacer atómica la operación" y no se pide en el encargo. Lo que sí cambia de fondo es **qué significa** ese log: hoy puede significar "se pagó pero no se actualizó el trust" (estado dividido, ambiguo); con esta corrección solo puede significar "no se aplicó ninguna de las dos cosas" (un único estado, sin ambigüedad, reconciliable manualmente sabiendo que hay que rehacer ambas).
- **`wallet_service.credit_reward` y `wallet_queries.update_wallet_on_task_complete` no se modifican** — siguen siendo el camino usado por `task_lifecycle.py`. La función nueva de esta sección es paralela, no un reemplazo.

#### 14.3.2 Nueva función `wallet_queries.credit_reward_and_update_trust`

```python
# app/db/queries/wallet_queries.py — función nueva
# Import nuevo en este módulo: from app.services import trust_score  (ver §14.3.1, excepción de capas)

def credit_reward_and_update_trust(
    provider_id: str,
    valid: bool,
    reward_amount: float,
    description: str,
) -> dict:
    """
    Aplica, en una única transacción psycopg2:
      - si valid: crédito atómico en wallets + registro en transactions
      - siempre: recálculo de accuracy/trust_score/rank del provider,
        con el provider bloqueado (FOR UPDATE) durante todo el cálculo
        para evitar carrera si dos chunks del mismo provider liquidan
        casi al mismo tiempo.
    Todo o nada: si cualquier paso falla, no se aplica ninguno (rollback
    automático al salir del `with conn:` por excepción).
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            # 1. Lock + lectura de los componentes de trust del provider
            cur.execute("""
                SELECT accuracy, completion_rate, response_time_score, client_rating
                FROM providers
                WHERE id = %s
                FOR UPDATE
            """, (provider_id,))
            provider = cur.fetchone()
            if provider is None:
                raise ValueError(f"Provider {provider_id} no encontrado")

            # 2. Cálculo en Python — mismas funciones puras que usa el resto del proyecto
            if valid:
                new_accuracy = trust_score.update_accuracy_on_complete(float(provider["accuracy"]))
            else:
                new_accuracy = trust_score.update_accuracy_on_fail(float(provider["accuracy"]))
            new_trust_score = trust_score.calculate_trust_score(
                completion_rate=float(provider["completion_rate"]),
                accuracy=new_accuracy,
                response_time_score=float(provider["response_time_score"]),
                client_rating=float(provider["client_rating"]),
            )
            new_rank = trust_score.get_rank(new_trust_score)

            # 3. Crédito de wallet + transacción (solo si valid) — misma aritmética
            #    que update_wallet_on_task_complete, sobre la MISMA conexión/transacción
            if valid:
                cur.execute("""
                    UPDATE wallets
                    SET available_balance = available_balance + %s,
                        total_earned      = total_earned + %s
                    WHERE provider_id = %s
                    RETURNING available_balance, total_earned
                """, (round(reward_amount, 2), round(reward_amount, 2), provider_id))
                wallet_row = cur.fetchone()
                if wallet_row is None:
                    raise ValueError(f"No wallet found for provider {provider_id}")

                cur.execute("""
                    INSERT INTO transactions (provider_id, amount, tx_type, description, status)
                    VALUES (%s, %s, 'pago_tarea', %s, 'completada')
                """, (provider_id, round(reward_amount, 2), description))

            # 4. Escritura de los nuevos valores de trust
            cur.execute("""
                UPDATE providers
                SET accuracy = %s, trust_score = %s, rank = %s
                WHERE id = %s
                RETURNING accuracy, trust_score, rank
            """, (new_accuracy, new_trust_score, new_rank, provider_id))
            updated_provider = cur.fetchone()

            conn.commit()

    return dict(updated_provider)
```

No se necesita `chunk_id` como parámetro (la descripción ya viene formada por el llamador, igual que hoy). `updated_at` de `providers` se actualiza solo mediante el trigger existente `trg_providers_updated_at` (BEFORE UPDATE), igual que con el UPDATE vía REST — no requiere ningún cambio.

#### 14.3.3 Cambios en `consensus_service._pay_and_update_trust`

La firma **no cambia** (`_pay_and_update_trust(provider_id: str, chunk_id: str, valid: bool) -> None`), así que ninguno de los tres puntos de llamada dentro de `process_chunk_submission` (acuerdo a 2 réplicas, mayoría a 3 réplicas, rechazo total a 3 réplicas) necesita tocarse. Solo cambian los imports y el cuerpo:

```python
# Imports que se ELIMINAN de consensus_service.py:
#   from app.db.queries.auth_queries import get_provider_by_id
#   from app.db.queries.profile_queries import update_provider
#   "wallet_service" del `from app.services import trust_score, wallet_service`
#     (queda `from app.services import trust_score`; wallet_service deja de usarse en este módulo)
# Import que se AÑADE:
#   from app.db.queries import wallet_queries

def _pay_and_update_trust(provider_id: str, chunk_id: str, valid: bool) -> None:
    """Pago (si valid) y actualización de trust, atómicos, para un resultado de chunk."""
    try:
        wallet_queries.credit_reward_and_update_trust(
            provider_id=str(provider_id),
            valid=valid,
            reward_amount=REWARD_PER_CHUNK,
            description=f"Recompensa por chunk validado: {chunk_id}",
        )
    except Exception as exc:
        logger.error(
            "Pago/trust (transaccional) fallido para proveedor %s, chunk %s — "
            "ninguna de las dos operaciones se aplicó, requiere reconciliación manual: %s",
            provider_id, chunk_id, exc, exc_info=True,
        )
```

#### 14.3.4 Qué NO cambia

- `SubmitRequest`/`SubmitResponse` (contrato de `/work/{chunk_id}/submit`) — sin cambios, ningún campo nuevo.
- `ClaimRequest`/`ClaimResponse` (contrato de `/work/claim`) — sin cambios; el TTL es enteramente interno.
- `docs/04-api-contracts.md` — no requiere cambios de contrato (request/response). Se añade únicamente una fila a la tabla de la columna nueva `assigned_at` en §6.1 (modelo de datos), de forma additiva, con referencia a esta sección.

---

### 14.4 Riesgos, dependencias y deuda residual

1. **Dependencia dura de `settings.supabase_db_url` como obligatorio.** Ambos diseños de esta sección (§14.2 y §14.3) asumen que sigue siendo `str` obligatorio en `config.py`, no `Optional`. Esto es cierto hoy (§14.0.6) pero ya se debilitó una vez en un WIP sin commitear (`docs/05-review.md`, R3-CRIT-02). Si ese WIP (u otro equivalente) reaparece, ambas correcciones de esta sección degradarían en silencio a errores de socket confusos en vez de fail-fast — exactamente el riesgo ya documentado allí. No se requiere acción ahora; se deja constancia para que quien revise ese WIP en el futuro sepa que el radio de impacto también alcanza el reclamo de chunks y el pago de recompensas.

2. **Más conexiones psycopg2 por request, sin pool.** `claim_chunks_atomic` sigue abriendo una única conexión por llamada (antes y después de este diseño — las 3 sentencias van sobre la misma conexión), pero `credit_reward_and_update_trust` añade una conexión psycopg2 nueva por cada resultado de chunk liquidado (antes eran 0 conexiones psycopg2 en esta ruta — usaba REST). Esto es consistente con el patrón ya usado en el resto del proyecto, pero acentúa la deuda ya señalada en A-06/R2-INFO-01 (ausencia de pooling). No se resuelve aquí — sigue siendo un ítem de deuda separado, ahora con un motivo más para priorizarlo.

3. **Fallo total de `credit_reward_and_update_trust` sigue sin reintento ni compensación automática** — solo logging (§14.3.1). Esto es una decisión deliberada de alcance (ver esa sección), no un olvido: cerrar esto del todo requeriría un patrón de reintento u outbox, que es explícitamente "medio/largo plazo" tanto en R2-C-03 como en el criterio de esta iniciativa. Queda como candidato para v4 si la tasa de fallos observada en producción lo justifica.

4. **`task_lifecycle.py` tiene un patrón de riesgo análogo (pago + trust en pasos separados) fuera del alcance de esta iniciativa** — ver §14.3.1. Se deja documentado para una futura corrección simétrica, no se resuelve aquí.

5. **La limpieza de chunks ya atascados hoy en producción (si los hay) requiere una acción manual puntual del Database Engineer** al desplegar la migración — ver nota al final de §14.2.3. La migración en sí no hace backfill automático.

---

### 14.5 Handoff — Database Engineer

1. Crear y ejecutar **`migrations/006_chunk_ttl.sql`** (contenido exacto en §14.2.3): añade `chunks.assigned_at timestamptz NULL` + índice parcial `idx_chunks_assigned_at ON chunks(assigned_at) WHERE status='assigned'`. Idempotente, mismo estilo que `004_compute.sql`/`005_client.sql`.
2. Antes o durante el despliegue, valorar ejecutar una única vez (fuera del script idempotente, como paso operativo manual) un `UPDATE chunks SET status='pending', assigned_to=NULL WHERE status='assigned'` para liberar cualquier chunk ya atascado en el entorno actual — opcional pero recomendado, ver §14.2.3.
3. No se requiere ninguna migración para el Problema 2 (pago + trust): no hay cambio de esquema, solo de código de aplicación.
4. Confirmar que `SUPABASE_DB_URL` sigue siendo la variable de pool (puerto 6543) ya usada por el resto de operaciones psycopg2 del proyecto — no se introduce ninguna variable de entorno nueva.

### 14.6 Handoff — Backend Dev

**Problema 1 (TTL):**
1. `app/db/queries/compute_queries.py`: añadir constante `CHUNK_ASSIGNMENT_TTL_MINUTES = 10`; reescribir `claim_chunks_atomic` según §14.2.4 (3 sentencias secuenciales sobre una misma conexión/transacción; firma nueva `-> tuple[list[dict], list[str]]`); modificar `update_chunk_status` para poner `assigned_at = NULL` en el mismo `UPDATE` siempre que el nuevo `status` no sea `'assigned'` (además de lo que ya hace con `assigned_to`).
2. `app/services/consensus_service.py`: añadir `process_chunk_claim(provider_id, max_chunks) -> list[dict]` según §14.2.6 (llama a `compute_queries.claim_chunks_atomic` y luego a `_try_close_job` por cada job_id rechazado).
3. `app/routers/work.py`: cambiar la línea del endpoint `POST /claim` para llamar a `consensus_service.process_chunk_claim(...)` en vez de `compute_queries.claim_chunks_atomic(...)`; eliminar el import ahora muerto `from app.db.queries import compute_queries`.

**Problema 2 (pago + trust transaccional):**
4. `app/db/queries/wallet_queries.py`: añadir `credit_reward_and_update_trust(provider_id, valid, reward_amount, description) -> dict` según §14.3.2 (importa `app.services.trust_score` — excepción de capas documentada en §14.3.1, dejar comentario en el código señalándolo). Añadir imports `psycopg2`, `psycopg2.extras`, `from app.core.config import settings` si no están ya en el módulo (confirmar: hoy `wallet_queries.py` ya importa ambos).
5. `app/services/consensus_service.py`: reescribir el cuerpo de `_pay_and_update_trust` según §14.3.3 (misma firma). Eliminar imports `get_provider_by_id` (de `auth_queries`), `update_provider` (de `profile_queries`) y `wallet_service` (queda solo `trust_score` del `from app.services import ...`); añadir `from app.db.queries import wallet_queries`.
6. No tocar `wallet_service.credit_reward`, `wallet_queries.update_wallet_on_task_complete` ni `task_lifecycle.py` — quedan exactamente como están.

### 14.7 Impacto en tests existentes (para QA / Backend Dev)

- **`backend/tests/test_consensus.py`:** los tests que llegan a consenso (K-01, K-03, K-04 — los que hoy mockean `app.services.wallet_service.credit_reward`, `app.db.queries.auth_queries.get_provider_by_id` y `app.db.queries.profile_queries.update_provider`) dejan de ejercitar el código real una vez aplicado este diseño, porque `_pay_and_update_trust` ya no llama a esas tres funciones — deben actualizarse para mockear `app.db.queries.wallet_queries.credit_reward_and_update_trust` en su lugar. Es un cambio mecánico (un mock en vez de tres) pero necesario para que los tests sean honestos.
- **`claim_chunks_atomic` / `POST /work/claim`:** no tienen tests unitarios hoy (§14.0.7) — no hay nada que romper, pero se recomienda que QA/Backend Dev añadan al menos un test de integración (contra base de datos real de test, siguiendo el patrón "sin mocking de BD" ya usado para `test_compute.py` según §12.9) que cree un chunk `assigned` con `assigned_at` en el pasado y confirme que una llamada a `/work/claim` lo libera y permite que otro proveedor lo reclame. No es un requisito bloqueante de este diseño, es una recomendación a quien lo implemente.
