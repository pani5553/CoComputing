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
