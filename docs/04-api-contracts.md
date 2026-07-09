# Co-Computing — Contratos de API y Modelo de Datos

**Versión:** 1.0
**Fecha:** 2026-06-05
**Autor:** Software Architect
**Referencias:** `docs/01-stack.md`, `docs/02-requisitos.md`, `docs/02-backlog.md`

---

## Convenciones globales

| Aspecto | Regla |
|---------|-------|
| Base URL (desarrollo) | `http://localhost:8000` |
| Content-Type | `application/json` en todas las requests y responses |
| Autenticación | `Authorization: Bearer <jwt>` en todos los endpoints marcados como [AUTH] |
| JWT ausente o inválido | `401 Unauthorized` con body `{"detail": "No autenticado"}` |
| Recurso no propio | `403 Forbidden` con body `{"detail": "No tienes permiso para realizar esta acción"}` |
| Recurso no encontrado | `404 Not Found` con body `{"detail": "<mensaje legible>"}` |
| Error de validación | `422 Unprocessable Entity` con body Pydantic estándar |
| Error de negocio | `400 Bad Request` con body `{"detail": "<mensaje legible en español>"}` |
| Rate limit excedido | `429 Too Many Requests` con body `{"detail": "Demasiadas peticiones. Inténtalo de nuevo en unos instantes."}` y cabecera `Retry-After: <segundos>` — ver `docs/04-arquitectura.md` §15.1 (endurecimiento 2026-07-08) |
| Error de servidor | `500 Internal Server Error` con body `{"detail": "Error interno del servidor"}` |
| Campos de fecha | ISO 8601 en UTC: `"2026-06-05T14:32:00Z"` |
| Moneda | `float` con 2 decimales. La unidad es CC (Co-Computing Credits). |
| Paginación | Solo `GET /wallet/transactions` está paginada; el resto devuelve la lista completa acotada. |

---

## 1. Modelo de Datos

### 1.1 Tabla `providers`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `email` | `text` | NO | — | Único. Email del proveedor. |
| `full_name` | `text` | NO | — | Nombre completo. |
| `password_hash` | `text` | NO | — | bcrypt hash; nunca expuesto en API. |
| `trust_score` | `numeric(5,2)` | NO | `0.00` | 0.00 – 100.00 |
| `rank` | `text` | NO | `'nuevo'` | `nuevo` \| `confiable` \| `experto` \| `elite` |
| `tasks_completed` | `integer` | NO | `0` | Contador acumulado. |
| `success_rate` | `numeric(5,2)` | NO | `0.00` | % tareas completadas / (completadas + fallidas) |
| `total_earned` | `numeric(12,2)` | NO | `0.00` | Suma histórica de recompensas. |
| `completion_rate` | `numeric(5,2)` | NO | `0.00` | Componente del Trust Score (0-100). |
| `accuracy` | `numeric(5,2)` | NO | `80.00` | Componente del Trust Score (0-100). |
| `response_time_score` | `numeric(5,2)` | NO | `70.00` | Componente del Trust Score (0-100). |
| `client_rating` | `numeric(5,2)` | NO | `70.00` | Componente del Trust Score (fijo en MVP). |
| `cpu_model` | `text` | SÍ | `null` | Modelo de CPU autodeclarado. |
| `gpu_model` | `text` | SÍ | `null` | Modelo de GPU autodeclarado. |
| `ram_gb` | `integer` | SÍ | `null` | RAM en GB (entero > 0). |
| `storage_gb` | `integer` | SÍ | `null` | Almacenamiento en GB (entero > 0). |
| `is_online` | `boolean` | NO | `false` | Toggle manual de disponibilidad. |
| `created_at` | `timestamptz` | NO | `now()` | Fecha de registro. |
| `updated_at` | `timestamptz` | NO | `now()` | Actualización automática (trigger). |

**Restricciones:**
- `UNIQUE (email)`
- `CHECK (trust_score >= 0 AND trust_score <= 100)`
- `CHECK (rank IN ('nuevo', 'confiable', 'experto', 'elite'))`

---

### 1.2 Tabla `tasks`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `title` | `text` | NO | — | Título de la tarea. |
| `task_type` | `text` | NO | — | `renderizado_3d` \| `entrenamiento_ml` \| `transcodificacion_video` \| `analisis_datos` \| `simulacion_fisica` |
| `description` | `text` | NO | — | Descripción completa. |
| `reward` | `numeric(10,2)` | NO | — | Recompensa en CC. |
| `duration_min` | `integer` | NO | — | Duración estimada mínima (minutos). |
| `duration_max` | `integer` | NO | — | Duración estimada máxima (minutos). |
| `difficulty` | `text` | NO | — | `facil` \| `medio` \| `dificil` |
| `hardware_required` | `text` | NO | — | `cpu` \| `gpu` \| `mixto` |
| `total_slots` | `integer` | NO | — | Plazas totales disponibles. |
| `slots_left` | `integer` | NO | — | Plazas restantes (decrementa al aceptar). |
| `stages` | `text[]` | NO | — | Array de nombres de etapas (4-6 etapas). |
| `requester_name` | `text` | NO | — | Nombre del solicitante (dato de seed). |
| `status` | `text` | NO | `'disponible'` | `disponible` \| `en_progreso` \| `completada` \| `cancelada` |
| `created_at` | `timestamptz` | NO | `now()` | Fecha de creación. |
| `updated_at` | `timestamptz` | NO | `now()` | Actualización automática (trigger). |

**Restricciones:**
- `CHECK (slots_left >= 0 AND slots_left <= total_slots)`
- `CHECK (difficulty IN ('facil', 'medio', 'dificil'))`
- `CHECK (hardware_required IN ('cpu', 'gpu', 'mixto'))`
- `CHECK (status IN ('disponible', 'en_progreso', 'completada', 'cancelada'))`
- `CHECK (duration_min > 0 AND duration_max >= duration_min)`
- `CHECK (reward > 0)`

---

### 1.3 Tabla `task_assignments`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `task_id` | `uuid` | NO | — | FK → `tasks.id` |
| `provider_id` | `uuid` | NO | — | FK → `providers.id` |
| `status` | `text` | NO | `'aceptada'` | `aceptada` \| `procesando` \| `completada` \| `fallida` \| `cancelada` |
| `reward_paid` | `numeric(10,2)` | SÍ | `null` | Recompensa pagada al completar. |
| `trust_delta` | `numeric(5,2)` | SÍ | `null` | Cambio en Trust Score por esta asignación. |
| `accepted_at` | `timestamptz` | NO | `now()` | Timestamp de aceptación. |
| `started_at` | `timestamptz` | SÍ | `null` | Timestamp de inicio (POST /start). |
| `completed_at` | `timestamptz` | SÍ | `null` | Timestamp de completado o fallo. |
| `created_at` | `timestamptz` | NO | `now()` | |
| `updated_at` | `timestamptz` | NO | `now()` | |

**Restricciones:**
- `CHECK (status IN ('aceptada', 'procesando', 'completada', 'fallida', 'cancelada'))`
- `UNIQUE (task_id, provider_id)` — un proveedor no puede aceptar la misma tarea dos veces (la constraint se aplica solo si el status previo es terminal; ver lógica en `task_lifecycle.py`)

**Índices:**
- `idx_task_assignments_provider_id` en `(provider_id)`
- `idx_task_assignments_task_id` en `(task_id)`
- `idx_task_assignments_status` en `(status)`

---

### 1.4 Tabla `wallets`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `provider_id` | `uuid` | NO | — | FK → `providers.id`, UNIQUE (relación 1:1) |
| `available_balance` | `numeric(12,2)` | NO | `0.00` | Saldo listo para retirar. |
| `pending_balance` | `numeric(12,2)` | NO | `0.00` | Saldo en proceso (0 en MVP simplificado). |
| `total_earned` | `numeric(12,2)` | NO | `0.00` | Suma histórica de ingresos. |
| `total_withdrawn` | `numeric(12,2)` | NO | `0.00` | Suma histórica de retiros. |
| `created_at` | `timestamptz` | NO | `now()` | |
| `updated_at` | `timestamptz` | NO | `now()` | |

**Restricciones:**
- `UNIQUE (provider_id)`
- `CHECK (available_balance >= 0)`
- `CHECK (pending_balance >= 0)`

---

### 1.5 Tabla `transactions`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `provider_id` | `uuid` | NO | — | FK → `providers.id` |
| `task_id` | `uuid` | SÍ | `null` | FK → `tasks.id` (null para retiros y bonos) |
| `amount` | `numeric(10,2)` | NO | — | Positivo para ingresos, positivo también para retiros (el tipo indica la dirección). |
| `tx_type` | `text` | NO | — | `pago_tarea` \| `retiro` \| `bonus` \| `penalizacion` |
| `status` | `text` | NO | `'completada'` | `completada` \| `pendiente` \| `cancelada` |
| `description` | `text` | NO | — | Descripción legible en español. |
| `withdraw_method` | `text` | SÍ | `null` | `transferencia` \| `paypal` \| `cripto` (solo en retiros) |
| `withdraw_destination` | `text` | SÍ | `null` | IBAN / email PayPal / dirección wallet (solo en retiros) |
| `created_at` | `timestamptz` | NO | `now()` | |

**Restricciones:**
- `CHECK (tx_type IN ('pago_tarea', 'retiro', 'bonus', 'penalizacion'))`
- `CHECK (status IN ('completada', 'pendiente', 'cancelada'))`
- `CHECK (amount > 0)`

**Índices:**
- `idx_transactions_provider_id` en `(provider_id, created_at DESC)`

---

### 1.6 Relaciones entre tablas

```
providers (1) ──── (1) wallets
     │
     └──── (N) task_assignments (N) ──── (1) tasks
     │
     └──── (N) transactions
                    │
                    └── (opcional) tasks
```

---

### 1.7 Tabla `rate_limit_counters` (nueva — Endurecimiento de seguridad, 2026-07-08)

Ver diseño completo en `docs/04-arquitectura.md` §15.1. Contador de rate limiting compartido entre los procesos Uvicorn (`--workers 2`), respaldado por Postgres porque el proyecto no tiene Redis. Usada por `POST /auth/login`, `POST /auth/register`, `POST /work/claim` y `POST /work/{chunk_id}/submit`.

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `bucket` | `text` | NO | — | Identidad + scope del limitador, formato `"<scope>:<ip\|provider>:<identidad>"`, ej. `"login:ip:203.0.113.5"` o `"work_claim:provider:550e8400-..."` |
| `window_start` | `timestamptz` | NO | — | Inicio de la ventana fija (redondeado hacia abajo al múltiplo de `window_seconds` más cercano) |
| `request_count` | `integer` | NO | `0` | Peticiones contabilizadas en esta ventana para este bucket |

**Restricciones:**
- `PRIMARY KEY (bucket, window_start)` — también sirve de índice para el `UPSERT` atómico y para la limpieza perezoza de filas antiguas.

**Sin índices adicionales.** No tiene RLS ni políticas: se accede exclusivamente vía conexión psycopg2 directa (`SUPABASE_DB_URL`), nunca vía el SDK REST de Supabase — mismo patrón que `chunks`/`jobs` para operaciones que requieren atomicidad.

**Limpieza:** perezosa, sin scheduler — cada llamada a `check_rate_limit` borra, con 1% de probabilidad, las filas con `window_start` de más de 1 hora de antigüedad (mismo patrón de "reclamo perezoso sin scheduler" ya usado en §14.2.1 para el TTL de chunks).

---

## 2. Contratos de API

---

### 2.1 Módulo de Autenticación — `/auth`

---

#### `POST /auth/register`

Crea una nueva cuenta de proveedor. No requiere autenticación.

**Request body:**

```json
{
  "full_name": "Ana García",
  "email": "ana@example.com",
  "password": "mipassword123"
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `full_name` | string | Sí | min_length=1, max_length=100 |
| `email` | string (email) | Sí | Formato email válido |
| `password` | string | Sí | min_length=8 |

**Response 201 — Registro exitoso:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Ana García",
  "email": "ana@example.com",
  "trust_score": 0.00,
  "rank": "nuevo",
  "tasks_completed": 0,
  "success_rate": 0.00,
  "total_earned": 0.00,
  "is_online": false,
  "created_at": "2026-06-05T14:32:00Z"
}
```

**Efecto colateral:** Se crea automáticamente un registro en `wallets` con todos los saldos a 0.

**Response 409 — Email ya registrado:**

```json
{
  "detail": "Este email ya está registrado"
}
```

**Response 422 — Validación fallida (ejemplo: password corto):**

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "La contraseña debe tener al menos 8 caracteres",
      "input": "corta",
      "ctx": {"min_length": 8}
    }
  ]
}
```

**Response 429 — Límite de registros por IP excedido (5/hora, ver `docs/04-arquitectura.md` §15.1 y §15.4):**

```json
{
  "detail": "Demasiadas peticiones. Inténtalo de nuevo en unos instantes."
}
```

Cabecera de respuesta: `Retry-After: 3600`.

---

#### `POST /auth/login`

Autentica un proveedor y devuelve JWT. No requiere autenticación.

**Request body:**

```json
{
  "email": "ana@example.com",
  "password": "mipassword123"
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `email` | string (email) | Sí | Formato email válido |
| `password` | string | Sí | min_length=1 |

**Response 200 — Login exitoso:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800,
  "provider": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "Ana García",
    "email": "ana@example.com",
    "trust_score": 78.40,
    "rank": "experto",
    "tasks_completed": 24,
    "success_rate": 91.70,
    "total_earned": 48.75,
    "is_online": true,
    "cpu_model": "AMD Ryzen 9 5950X",
    "gpu_model": "NVIDIA RTX 4090",
    "ram_gb": 64,
    "storage_gb": 2000,
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

El JWT tiene claim `sub` = `provider.id` (UUID string) y `exp` = ahora + 7 días.

**Response 401 — Credenciales incorrectas (email no existe O password incorrecto):**

```json
{
  "detail": "Credenciales incorrectas"
}
```

El mensaje es idéntico en ambos casos para no revelar si el email existe.

**Response 429 — Límite de intentos por IP excedido (10/minuto, ver `docs/04-arquitectura.md` §15.1):**

```json
{
  "detail": "Demasiadas peticiones. Inténtalo de nuevo en unos instantes."
}
```

Cabecera de respuesta: `Retry-After: 60`.

---

#### `GET /auth/me` [AUTH]

Devuelve los datos completos del proveedor autenticado.

**Request:** Sin body. Header `Authorization: Bearer <token>` obligatorio.

**Response 200:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Ana García",
  "email": "ana@example.com",
  "trust_score": 78.40,
  "rank": "experto",
  "tasks_completed": 24,
  "success_rate": 91.70,
  "total_earned": 48.75,
  "completion_rate": 87.00,
  "accuracy": 82.00,
  "response_time_score": 70.00,
  "client_rating": 70.00,
  "is_online": true,
  "cpu_model": "AMD Ryzen 9 5950X",
  "gpu_model": "NVIDIA RTX 4090",
  "ram_gb": 64,
  "storage_gb": 2000,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-06-05T14:32:00Z"
}
```

**Response 401:** Token ausente, expirado o inválido.

---

### 2.2 Módulo de Tareas — `/tasks`

**Nota sobre el orden de rutas en FastAPI:** Las rutas literales (`/tasks/my/history`, `/tasks/assignments/{id}/progress`) deben registrarse **antes** que las rutas con parámetros (`/tasks/{id}`) para evitar conflictos de matching.

---

#### `GET /tasks/` [AUTH]

Listado de tareas disponibles con filtros opcionales.

**Query parameters:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `difficulty` | string | No | `facil` \| `medio` \| `dificil`. Múltiples valores separados por coma: `facil,medio` |
| `hardware` | string | No | `cpu` \| `gpu` \| `mixto`. Múltiples valores separados por coma. |
| `task_type` | string | No | Valor exacto del campo `task_type`. |
| `min_reward` | float | No | Recompensa mínima (inclusive). Debe ser > 0. |

Los filtros se aplican como AND. Solo se devuelven tareas con `status = 'disponible'` y `slots_left > 0`. Máximo 50 resultados ordenados por `reward DESC`.

**Response 200:**

```json
{
  "count": 3,
  "tasks": [
    {
      "id": "a1b2c3d4-...",
      "title": "Entrenamiento ML — ResNet-50 CIFAR-100",
      "task_type": "entrenamiento_ml",
      "description": "Entrenamiento completo de ResNet-50 sobre el dataset CIFAR-100...",
      "reward": 5.00,
      "duration_min": 45,
      "duration_max": 90,
      "difficulty": "dificil",
      "hardware_required": "gpu",
      "total_slots": 5,
      "slots_left": 2,
      "stages": [
        "Preparando entorno",
        "Descargando dataset",
        "Entrenando modelo",
        "Validando precisión",
        "Guardando checkpoints"
      ],
      "requester_name": "AI Research Lab",
      "status": "disponible",
      "created_at": "2026-06-01T00:00:00Z"
    }
  ]
}
```

**Response 200 — Sin resultados para los filtros:**

```json
{
  "count": 0,
  "tasks": []
}
```

**Response 400 — Valor de filtro inválido (ej. min_reward negativa):**

```json
{
  "detail": "El valor de recompensa mínima debe ser mayor que cero"
}
```

---

#### `GET /tasks/my/history` [AUTH]

Historial de asignaciones del proveedor autenticado (todas, ordenadas por fecha de creación descendente).

**Request:** Sin body ni query params adicionales.

**Response 200:**

```json
{
  "count": 5,
  "assignments": [
    {
      "id": "assign-uuid-1",
      "task_id": "task-uuid-1",
      "task_title": "Renderizado de escena nocturna 4K",
      "task_type": "renderizado_3d",
      "status": "completada",
      "reward_paid": 5.00,
      "trust_delta": 1.20,
      "accepted_at": "2026-06-04T12:00:00Z",
      "started_at": "2026-06-04T12:05:00Z",
      "completed_at": "2026-06-04T13:30:00Z"
    },
    {
      "id": "assign-uuid-2",
      "task_id": "task-uuid-2",
      "task_title": "Simulación de dinámica de fluidos",
      "task_type": "simulacion_fisica",
      "status": "fallida",
      "reward_paid": null,
      "trust_delta": -2.50,
      "accepted_at": "2026-06-03T09:00:00Z",
      "started_at": "2026-06-03T09:10:00Z",
      "completed_at": "2026-06-03T09:45:00Z"
    }
  ]
}
```

---

#### `GET /tasks/{task_id}` [AUTH]

Detalle completo de una tarea.

**Path parameter:** `task_id` (UUID)

**Response 200:**

```json
{
  "id": "a1b2c3d4-...",
  "title": "Entrenamiento ML — ResNet-50 CIFAR-100",
  "task_type": "entrenamiento_ml",
  "description": "Entrenamiento completo de ResNet-50 sobre el dataset CIFAR-100 con 200 épocas...",
  "reward": 5.00,
  "duration_min": 45,
  "duration_max": 90,
  "difficulty": "dificil",
  "hardware_required": "gpu",
  "total_slots": 5,
  "slots_left": 2,
  "stages": [
    "Preparando entorno",
    "Descargando dataset",
    "Entrenando modelo",
    "Validando precisión",
    "Guardando checkpoints"
  ],
  "requester_name": "AI Research Lab",
  "status": "disponible",
  "created_at": "2026-06-01T00:00:00Z",
  "active_assignment": null
}
```

Cuando el proveedor autenticado tiene una asignación activa para esta tarea, `active_assignment` contiene:

```json
"active_assignment": {
  "id": "assign-uuid-1",
  "status": "procesando",
  "accepted_at": "2026-06-05T14:00:00Z",
  "started_at": "2026-06-05T14:05:00Z"
}
```

**Response 404:**

```json
{
  "detail": "Tarea no encontrada"
}
```

---

#### `POST /tasks/{task_id}/accept` [AUTH]

Acepta una tarea y crea la asignación para el proveedor autenticado.

**Path parameter:** `task_id` (UUID)

**Request body:** Vacío `{}`

**Response 201 — Asignación creada:**

```json
{
  "id": "assign-uuid-nuevo",
  "task_id": "a1b2c3d4-...",
  "task_title": "Entrenamiento ML — ResNet-50 CIFAR-100",
  "provider_id": "550e8400-...",
  "status": "aceptada",
  "reward_paid": null,
  "trust_delta": null,
  "accepted_at": "2026-06-05T14:32:00Z",
  "started_at": null,
  "completed_at": null
}
```

**Efecto colateral:** `tasks.slots_left` decrementado en 1 de forma atómica.

**Response 400 — Sin plazas disponibles:**

```json
{
  "detail": "No quedan plazas disponibles para esta tarea"
}
```

**Response 400 — El proveedor ya tiene una asignación activa para esta tarea:**

```json
{
  "detail": "Ya tienes esta tarea activa"
}
```

**Response 404 — Tarea no encontrada:**

```json
{
  "detail": "Tarea no encontrada"
}
```

---

#### `POST /tasks/{task_id}/start` [AUTH]

Inicia el procesamiento de una tarea aceptada. El `task_id` en la ruta es el ID de la tarea (no de la asignación). El backend localiza la asignación activa del proveedor para esa tarea.

**Path parameter:** `task_id` (UUID)

**Request body:** Vacío `{}`

**Response 200 — Procesamiento iniciado:**

```json
{
  "assignment_id": "assign-uuid-1",
  "task_id": "a1b2c3d4-...",
  "status": "procesando",
  "started_at": "2026-06-05T14:35:00Z",
  "stages": [
    "Preparando entorno",
    "Descargando dataset",
    "Entrenando modelo",
    "Validando precisión",
    "Guardando checkpoints"
  ],
  "stages_count": 5,
  "duration_max_seconds": 5400
}
```

El campo `duration_max_seconds` = `tasks.duration_max * 60` y es necesario para que el frontend calcule el progreso esperado.

**Response 400 — Estado de asignación inválido (no está en "aceptada"):**

```json
{
  "detail": "Solo puedes iniciar una tarea que hayas aceptado previamente"
}
```

**Response 404 — No existe asignación activa del proveedor para esta tarea:**

```json
{
  "detail": "No tienes ninguna asignación activa para esta tarea"
}
```

---

#### `POST /tasks/{task_id}/complete` [AUTH]

Completa una tarea en procesamiento. El `task_id` es el ID de la tarea.

**Path parameter:** `task_id` (UUID)

**Request body:** Vacío `{}`

**Response 200 — Tarea completada:**

```json
{
  "assignment_id": "assign-uuid-1",
  "task_id": "a1b2c3d4-...",
  "status": "completada",
  "reward_paid": 5.00,
  "trust_delta": 1.20,
  "new_trust_score": 79.60,
  "new_rank": "experto",
  "completed_at": "2026-06-05T15:20:00Z"
}
```

**Efectos colaterales:**
1. `task_assignments.status` → `'completada'`, `completed_at` registrado, `reward_paid` y `trust_delta` actualizados.
2. `wallets.available_balance` += `reward`, `total_earned` += `reward`.
3. `transactions` — nueva fila tipo `pago_tarea`, status `completada`.
4. `providers.tasks_completed` += 1, `trust_score`, `rank`, `completion_rate`, `accuracy`, `response_time_score`, `success_rate` recalculados.

**Response 400 — La asignación no está en estado "procesando":**

```json
{
  "detail": "Solo puedes completar una tarea que esté en procesamiento"
}
```

**Response 403 — El proveedor no es el dueño de la asignación:**

```json
{
  "detail": "No tienes permiso para realizar esta acción"
}
```

---

#### `POST /tasks/{task_id}/fail` [AUTH]

Reporta fallo en una tarea en procesamiento.

**Path parameter:** `task_id` (UUID)

**Request body:** Vacío `{}`

**Response 200 — Fallo registrado:**

```json
{
  "assignment_id": "assign-uuid-1",
  "task_id": "a1b2c3d4-...",
  "status": "fallida",
  "reward_paid": null,
  "trust_delta": -2.50,
  "new_trust_score": 75.90,
  "new_rank": "experto",
  "completed_at": "2026-06-05T15:10:00Z"
}
```

**Efectos colaterales:**
1. `task_assignments.status` → `'fallida'`, `completed_at` registrado, `trust_delta` (negativo) actualizado.
2. No se acredita ninguna recompensa.
3. `providers.trust_score`, `rank`, `accuracy`, `response_time_score`, `success_rate` recalculados.

**Response 400 — La asignación no está en estado "procesando":**

```json
{
  "detail": "Solo puedes reportar fallo en una tarea que esté en procesamiento"
}
```

---

#### `GET /tasks/assignments/{assignment_id}/progress` [AUTH]

Consulta el progreso simulado de una asignación en procesamiento. Diseñado para polling cada 3 segundos; debe responder en < 200 ms.

**Path parameter:** `assignment_id` (UUID)

**Response 200 — Asignación en "procesando":**

```json
{
  "assignment_id": "assign-uuid-1",
  "task_id": "a1b2c3d4-...",
  "task_title": "Entrenamiento ML — ResNet-50 CIFAR-100",
  "status": "procesando",
  "progress": 45.3,
  "current_stage_index": 2,
  "stages": [
    "Preparando entorno",
    "Descargando dataset",
    "Entrenando modelo",
    "Validando precisión",
    "Guardando checkpoints"
  ],
  "started_at": "2026-06-05T14:35:00Z",
  "can_complete": true
}
```

Lógica de cálculo en el backend:
- `elapsed = now() - started_at` (en segundos)
- `progress = min((elapsed / duration_max_seconds) * 100, 99.0)`
- `progress` se devuelve redondeado a 1 decimal
- `current_stage_index = min(floor((progress / 100) * len(stages)), len(stages) - 1)`
- `can_complete = progress >= 80.0`

**Response 200 — Asignación en estado "aceptada" (aún no iniciada):**

```json
{
  "assignment_id": "assign-uuid-1",
  "task_id": "a1b2c3d4-...",
  "task_title": "Entrenamiento ML — ResNet-50 CIFAR-100",
  "status": "aceptada",
  "progress": 0.0,
  "current_stage_index": 0,
  "stages": ["Preparando entorno", "Descargando dataset", "Entrenando modelo", "Validando precisión", "Guardando checkpoints"],
  "started_at": null,
  "can_complete": false
}
```

**Response 200 — Asignación en estado terminal ("completada" o "fallida"):**

```json
{
  "assignment_id": "assign-uuid-1",
  "task_id": "a1b2c3d4-...",
  "task_title": "Entrenamiento ML — ResNet-50 CIFAR-100",
  "status": "completada",
  "progress": 100.0,
  "current_stage_index": 4,
  "stages": ["Preparando entorno", "Descargando dataset", "Entrenando modelo", "Validando precisión", "Guardando checkpoints"],
  "started_at": "2026-06-05T14:35:00Z",
  "can_complete": false
}
```

El frontend debe detectar `status === 'completada'` o `status === 'fallida'` y redirigir automáticamente.

**Response 403 — El proveedor no es el dueño:**

```json
{
  "detail": "No tienes permiso para realizar esta acción"
}
```

**Response 404 — Asignación no encontrada:**

```json
{
  "detail": "Asignación no encontrada"
}
```

---

### 2.3 Módulo de Cartera — `/wallet`

---

#### `GET /wallet/` [AUTH]

Devuelve los saldos actuales de la cartera del proveedor autenticado.

**Response 200:**

```json
{
  "id": "wallet-uuid-1",
  "provider_id": "550e8400-...",
  "available_balance": 12.50,
  "pending_balance": 0.00,
  "total_earned": 48.75,
  "total_withdrawn": 36.25,
  "updated_at": "2026-06-05T15:20:00Z"
}
```

---

#### `GET /wallet/transactions` [AUTH]

Historial de transacciones paginado.

**Query parameters:**

| Parámetro | Tipo | Requerido | Defecto | Descripción |
|-----------|------|-----------|---------|-------------|
| `limit` | integer | No | 50 | Máximo de resultados. Máximo permitido: 50. |
| `offset` | integer | No | 0 | Desplazamiento para paginación. |

**Response 200:**

```json
{
  "count": 5,
  "total": 23,
  "transactions": [
    {
      "id": "tx-uuid-1",
      "provider_id": "550e8400-...",
      "task_id": "a1b2c3d4-...",
      "amount": 5.00,
      "tx_type": "pago_tarea",
      "status": "completada",
      "description": "Recompensa por tarea: Entrenamiento ML — ResNet-50 CIFAR-100",
      "withdraw_method": null,
      "withdraw_destination": null,
      "created_at": "2026-06-05T15:20:00Z"
    },
    {
      "id": "tx-uuid-2",
      "provider_id": "550e8400-...",
      "task_id": null,
      "amount": 10.00,
      "tx_type": "retiro",
      "status": "pendiente",
      "description": "Solicitud de retiro via PayPal",
      "withdraw_method": "paypal",
      "withdraw_destination": "ana@paypal.com",
      "created_at": "2026-06-04T09:00:00Z"
    }
  ]
}
```

Las transacciones se ordenan por `created_at DESC`.

---

#### `POST /wallet/withdraw` [AUTH]

Registra una solicitud de retiro de fondos.

**Request body:**

```json
{
  "amount": 10.00,
  "method": "paypal",
  "destination": "ana@paypal.com"
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `amount` | float | Sí | > 0, máximo 2 decimales, >= 10.0 |
| `method` | string | Sí | `transferencia` \| `paypal` \| `cripto` |
| `destination` | string | Sí | min_length=1, max_length=200 |

**Response 200 — Retiro registrado:**

```json
{
  "transaction_id": "tx-uuid-nuevo",
  "amount": 10.00,
  "method": "paypal",
  "destination": "ana@paypal.com",
  "status": "pendiente",
  "new_available_balance": 2.50,
  "message": "Solicitud de retiro registrada. Te contactaremos cuando se procese."
}
```

**Efectos colaterales:**
1. `wallets.available_balance` -= `amount`, `total_withdrawn` += `amount`.
2. `transactions` — nueva fila tipo `retiro`, status `pendiente`.

**Response 400 — Saldo insuficiente:**

```json
{
  "detail": "El monto supera tu saldo disponible (12,50 CC)"
}
```

**Response 400 — Monto inferior al mínimo:**

```json
{
  "detail": "El monto mínimo de retiro es 10,00 CC"
}
```

**Response 400 — Método inválido:**

Gestionado por validación Pydantic → 422.

---

### 2.4 Módulo de Perfil — `/profile`

---

#### `GET /profile/stats` [AUTH]

Devuelve el perfil completo del proveedor con desglose de Trust Score y hardware.

**Response 200:**

```json
{
  "id": "550e8400-...",
  "full_name": "Ana García",
  "email": "ana@example.com",
  "trust_score": 78.40,
  "rank": "experto",
  "tasks_completed": 24,
  "success_rate": 91.70,
  "total_earned": 48.75,
  "is_online": true,
  "created_at": "2026-01-01T00:00:00Z",
  "trust_score_detail": {
    "completion_rate": 87.00,
    "completion_rate_weight": 0.40,
    "accuracy": 82.00,
    "accuracy_weight": 0.30,
    "response_time_score": 70.00,
    "response_time_weight": 0.20,
    "client_rating": 70.00,
    "client_rating_weight": 0.10
  },
  "rank_info": {
    "current_rank": "experto",
    "current_rank_min": 75,
    "current_rank_max": 89,
    "next_rank": "elite",
    "next_rank_min": 90,
    "points_to_next_rank": 11.60
  },
  "hardware": {
    "cpu_model": "AMD Ryzen 9 5950X",
    "gpu_model": "NVIDIA RTX 4090",
    "ram_gb": 64,
    "storage_gb": 2000
  }
}
```

Cuando el proveedor es de rango `elite`, `next_rank` y `points_to_next_rank` son `null`.

---

#### `PUT /profile/hardware` [AUTH]

Actualiza las especificaciones de hardware del proveedor.

**Request body:**

```json
{
  "cpu_model": "AMD Ryzen 9 5950X",
  "gpu_model": "NVIDIA RTX 4090",
  "ram_gb": 64,
  "storage_gb": 2000
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `cpu_model` | string | Sí | min_length=1, max_length=200 |
| `gpu_model` | string \| null | No | max_length=200 o null |
| `ram_gb` | integer | Sí | ge=1 |
| `storage_gb` | integer | Sí | ge=1 |

**Response 200:**

```json
{
  "cpu_model": "AMD Ryzen 9 5950X",
  "gpu_model": "NVIDIA RTX 4090",
  "ram_gb": 64,
  "storage_gb": 2000,
  "updated_at": "2026-06-05T16:00:00Z"
}
```

**Response 422 — Validación fallida (ej. ram_gb = 0):**

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "ram_gb"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0,
      "ctx": {"ge": 1}
    }
  ]
}
```

---

#### `PATCH /profile/online` [AUTH]

Cambia el estado online del proveedor.

**Request body:**

```json
{
  "is_online": true
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `is_online` | boolean | Sí | — |

**Response 200:**

```json
{
  "is_online": true,
  "updated_at": "2026-06-05T16:05:00Z"
}
```

---

#### `PATCH /profile/name` [AUTH]

Actualiza el nombre completo del proveedor.

**Request body:**

```json
{
  "full_name": "Ana García López"
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `full_name` | string | Sí | min_length=1, max_length=100 |

**Response 200:**

```json
{
  "full_name": "Ana García López",
  "updated_at": "2026-06-05T16:10:00Z"
}
```

---

## 3. Resumen de Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/auth/register` | No | Registro de nuevo proveedor |
| `POST` | `/auth/login` | No | Login y obtención de JWT |
| `GET` | `/auth/me` | Sí | Datos del proveedor autenticado |
| `GET` | `/tasks/` | Sí | Listado de tareas con filtros |
| `GET` | `/tasks/my/history` | Sí | Historial de asignaciones propias |
| `GET` | `/tasks/{task_id}` | Sí | Detalle de tarea |
| `POST` | `/tasks/{task_id}/accept` | Sí | Aceptar tarea |
| `POST` | `/tasks/{task_id}/start` | Sí | Iniciar procesamiento |
| `POST` | `/tasks/{task_id}/complete` | Sí | Completar tarea |
| `POST` | `/tasks/{task_id}/fail` | Sí | Reportar fallo |
| `GET` | `/tasks/assignments/{assignment_id}/progress` | Sí | Progreso de una asignación |
| `GET` | `/wallet/` | Sí | Saldos de cartera |
| `GET` | `/wallet/transactions` | Sí | Historial de transacciones |
| `POST` | `/wallet/withdraw` | Sí | Solicitar retiro |
| `GET` | `/profile/stats` | Sí | Estadísticas y Trust Score |
| `PUT` | `/profile/hardware` | Sí | Actualizar hardware |
| `PATCH` | `/profile/online` | Sí | Toggle estado online |
| `PATCH` | `/profile/name` | Sí | Actualizar nombre |

---

## 4. Fórmulas de Negocio

### 4.1 Trust Score

```
trust_score = (completion_rate * 0.40) + (accuracy * 0.30)
            + (response_time_score * 0.20) + (client_rating * 0.10)
```

Todos los componentes tienen rango [0, 100]. El resultado se redondea a 2 decimales y se limita a [0.00, 100.00].

### 4.2 Rangos

| Rango | Trust Score mínimo | Trust Score máximo |
|-------|-------------------|-------------------|
| `nuevo` | 0.00 | 49.99 |
| `confiable` | 50.00 | 74.99 |
| `experto` | 75.00 | 89.99 |
| `elite` | 90.00 | 100.00 |

### 4.3 Actualización de componentes al completar/fallar

| Evento | `completion_rate` | `accuracy` | `response_time_score` |
|--------|-------------------|------------|----------------------|
| Completar | `completadas / (completadas + fallidas) * 100` | `min(accuracy + 2, 100)` | +5 si `started_at - accepted_at < 10 min`, -5 si > 60 min, sin cambio en otro caso |
| Fallar | `completadas / (completadas + fallidas) * 100` | `max(accuracy - 5, 0)` | -5 si `started_at - accepted_at > 60 min`, sin cambio en otro caso |

`client_rating` permanece en 70.00 durante todo el MVP.

### 4.4 Progreso simulado

```
progress = min((elapsed_seconds / duration_max_seconds) * 100, 99.0)
```

Donde `elapsed_seconds = (now_utc - started_at).total_seconds()` y `duration_max_seconds = task.duration_max * 60`.

### 4.5 Tasa de éxito

```
success_rate = (tasks_completed / total_finalized) * 100
```

Donde `total_finalized = tasks_completed + tasks_failed`. Si `total_finalized = 0`, `success_rate = 0.00`.

---

## 5. Errores HTTP — Referencia rápida

| Código | Causa típica | Mensaje de ejemplo |
|--------|-------------|---------------------|
| 400 | Violación de regla de negocio | "No quedan plazas disponibles para esta tarea" |
| 401 | Token ausente, expirado o inválido | "No autenticado" |
| 403 | Operación sobre recurso ajeno | "No tienes permiso para realizar esta acción" |
| 404 | Recurso inexistente | "Tarea no encontrada" |
| 409 | Conflicto de unicidad | "Este email ya está registrado" |
| 422 | Error de validación Pydantic | Estructura estándar Pydantic v2 |
| 500 | Error no controlado del servidor | "Error interno del servidor" |

Los mensajes 401, 403 y 500 son genéricos y no exponen detalles internos.

---

## 6. Compute API — Cómputo Real Distribuido

Esta sección documenta el pipeline de cómputo distribuido añadido en la feature "Cómputo Real". Todos los endpoints son adicionales; ningún contrato de las secciones anteriores se modifica.

---

### 6.1 Modelo de Datos — Tablas nuevas

#### Tabla `jobs`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `client_id` | `uuid` | NO | — | FK → `providers.id`. El proveedor que actúa como cliente del job. |
| `job_type` | `text` | NO | — | `data-processing`. Extensible con futuros tipos. |
| `status` | `text` | NO | `'pending'` | `pending` \| `splitting` \| `processing` \| `validating` \| `completed` \| `failed` |
| `params` | `jsonb` | NO | `{}` | Para `data-processing`: `{"operation":"mean","columns":["col1"]}` |
| `total_chunks` | `integer` | NO | `0` | Total de chunks en que se dividió el job. Fijado durante `splitting`. |
| `completed_chunks` | `integer` | NO | `0` | Chunks ya validados. Incrementado atómicamente al validar cada chunk. |
| `reward_total` | `numeric(10,2)` | NO | `0.00` | Recompensa total del job en CC. Distribuida entre proveedores con resultados válidos. |
| `result` | `jsonb` | SÍ | `null` | Resultado consolidado. NULL hasta que el job alcance `completed`. |
| `created_at` | `timestamptz` | NO | `now()` | |
| `completed_at` | `timestamptz` | SÍ | `null` | Timestamp al alcanzar `completed` o `failed`. |

**Restricciones:**
- `CHECK (job_type IN ('data-processing'))`
- `CHECK (status IN ('pending', 'splitting', 'processing', 'validating', 'completed', 'failed'))`
- `CHECK (total_chunks >= 0)`
- `CHECK (completed_chunks >= 0)`
- `CHECK (completed_chunks <= total_chunks)`
- `CHECK (reward_total >= 0.00)`

**Índices:**
- `idx_jobs_client_id` en `(client_id)`
- `idx_jobs_status` en `(status)`
- `idx_jobs_client_status` en `(client_id, status)`

---

#### Tabla `chunks`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `job_id` | `uuid` | NO | — | FK → `jobs.id` ON DELETE CASCADE |
| `chunk_index` | `integer` | NO | — | Posición ordinal dentro del job. Empieza en 0. |
| `payload` | `jsonb` | NO | — | Para `data-processing`: `{"rows":[[...]],"columns":["col1"]}` |
| `status` | `text` | NO | `'pending'` | `pending` \| `assigned` \| `done` \| `rejected` |
| `assigned_to` | `uuid` | SÍ | `null` | FK → `providers.id`. NULL cuando está `pending` o `rejected`. |
| `assigned_at` | `timestamptz` | SÍ | `null` | **v3.** Timestamp de la asignación vigente. NULL si `status != 'assigned'`. Usado para el TTL de reclamo perezoso (10 min) — ver `docs/04-arquitectura.md` §14.2. |
| `attempts` | `integer` | NO | `0` | Veces que el scheduler ha intentado asignar este chunk. |
| `replicas_needed` | `integer` | NO | `2` | Número de proveedores distintos que deben procesar el chunk para consenso. |
| `created_at` | `timestamptz` | NO | `now()` | |

**Restricciones:**
- `UNIQUE (job_id, chunk_index)`
- `CHECK (status IN ('pending', 'assigned', 'done', 'rejected'))`
- `CHECK (chunk_index >= 0)`
- `CHECK (attempts >= 0)`
- `CHECK (replicas_needed >= 1)`

**Índices:**
- `idx_chunks_job_id` en `(job_id)`
- `idx_chunks_status` en `(status)`
- `idx_chunks_job_status` en `(job_id, status)`
- `idx_chunks_assigned_to` parcial en `(assigned_to) WHERE assigned_to IS NOT NULL`
- `idx_chunks_assigned_at` parcial en `(assigned_at) WHERE status = 'assigned'` — **v3**, `migrations/006_chunk_ttl.sql`

**Nota sobre `replicas_needed` vs `assigned_to`:** La columna `assigned_to` registra solo al proveedor con asignación activa más reciente (para reintento). El conteo real de resultados entregados se obtiene de `chunk_results`. El claim atómico lee `chunk_results` para determinar cuántas réplicas faltan antes de marcar el chunk como `done`.

---

#### Tabla `chunk_results`

| Campo | Tipo PostgreSQL | Nulo | Defecto | Descripción |
|-------|----------------|------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | PK |
| `chunk_id` | `uuid` | NO | — | FK → `chunks.id` ON DELETE CASCADE |
| `provider_id` | `uuid` | NO | — | FK → `providers.id` ON DELETE RESTRICT |
| `result` | `jsonb` | NO | — | Resultado del cómputo del chunk por este proveedor. |
| `duration_ms` | `integer` | NO | — | Tiempo de procesamiento en ms reportado por el worker. > 0. |
| `is_valid` | `boolean` | SÍ | `null` | `null`=pendiente, `true`=válido por consenso, `false`=rechazado. |
| `created_at` | `timestamptz` | NO | `now()` | |

**Restricciones:**
- `UNIQUE (chunk_id, provider_id)` — un proveedor solo puede entregar un resultado por chunk
- `CHECK (duration_ms > 0)`

**Índices:**
- `idx_chunk_results_chunk_id` en `(chunk_id)`
- `idx_chunk_results_provider_id` en `(provider_id)`
- `idx_chunk_results_is_valid` en `(chunk_id, is_valid)`

---

#### 6.1.1 Relaciones entre tablas nuevas y existentes

```
providers (1) ──── (N) jobs          [client_id → providers.id]
providers (1) ──── (N) chunks        [assigned_to → providers.id, nullable]
providers (1) ──── (N) chunk_results [provider_id → providers.id]

jobs (1) ──── (N) chunks             [job_id → jobs.id, CASCADE DELETE]
chunks (1) ──── (N) chunk_results    [chunk_id → chunks.id, CASCADE DELETE]
```

---

### 6.2 Tipos Pydantic (backend) y TypeScript (frontend)

#### Pydantic — `app/models/compute.py`

```python
from uuid import UUID
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    job_type: str = Field(..., pattern="^data-processing$")
    params: dict[str, Any]
    # El CSV se sube como multipart/form-data; este modelo cubre el body JSON puro.
    # Para CSV: endpoint acepta UploadFile + params como Form field (JSON string).

class JobPublic(BaseModel):
    id: UUID
    client_id: UUID
    job_type: str
    status: str
    params: dict[str, Any]
    total_chunks: int
    completed_chunks: int
    reward_total: float
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None
    progress: float   # campo calculado: completed_chunks / total_chunks * 100

class JobListResponse(BaseModel):
    count: int
    jobs: list[JobPublic]

# ── Chunks ────────────────────────────────────────────────────────────────────

class ChunkPublic(BaseModel):
    id: UUID
    job_id: UUID
    chunk_index: int
    status: str
    assigned_to: UUID | None
    attempts: int
    replicas_needed: int
    created_at: datetime
    # payload NO se expone al cliente (puede contener datos grandes)

class ClaimResponse(BaseModel):
    chunks: list[ChunkWithPayload]

class ChunkWithPayload(BaseModel):
    chunk_id: UUID
    job_id: UUID
    chunk_index: int
    job_type: str
    payload: dict[str, Any]   # datos reales para procesar

# ── Submit ────────────────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    result: dict[str, Any]
    duration_ms: int = Field(..., gt=0)

class SubmitResponse(BaseModel):
    chunk_result_id: UUID
    chunk_id: UUID
    status: str              # estado del chunk tras submit: "assigned" | "done"
    message: str
```

#### TypeScript — `frontend/src/types/compute.ts`

```typescript
export type JobStatus =
  | 'pending'
  | 'splitting'
  | 'processing'
  | 'validating'
  | 'completed'
  | 'failed';

export type ChunkStatus = 'pending' | 'assigned' | 'done' | 'rejected';

export interface Job {
  id: string;
  client_id: string;
  job_type: string;
  status: JobStatus;
  params: Record<string, unknown>;
  total_chunks: number;
  completed_chunks: number;
  reward_total: number;
  result: Record<string, unknown> | null;
  created_at: string;       // ISO 8601 UTC
  completed_at: string | null;
  progress: number;         // 0–100, calculado por el backend
}

export interface JobListResponse {
  count: number;
  jobs: Job[];
}

export interface ChunkWithPayload {
  chunk_id: string;
  job_id: string;
  chunk_index: number;
  job_type: string;
  payload: Record<string, unknown>;
}

export interface ClaimResponse {
  chunks: ChunkWithPayload[];
}

export interface SubmitRequest {
  result: Record<string, unknown>;
  duration_ms: number;
}

export interface SubmitResponse {
  chunk_result_id: string;
  chunk_id: string;
  status: ChunkStatus;
  message: string;
}

export interface JobCreateRequest {
  job_type: 'data-processing';
  params: {
    operation: 'mean' | 'sum' | 'min' | 'max' | 'count';
    columns?: string[];
  };
}
```

---

### 6.3 Endpoints del Router `/jobs` (lado cliente)

**Prefijo registrado en `app/main.py`:** `/jobs`
**Módulo:** `app/routers/compute.py`
**Auth:** Todos los endpoints requieren `[AUTH]` (Bearer JWT).

---

#### `POST /jobs` [AUTH]

Crea un nuevo job de cómputo. Admite dos variantes de body:

**Variante A — JSON puro (datos embebidos en `params`):**

```
Content-Type: application/json
```

```json
{
  "job_type": "data-processing",
  "params": {
    "operation": "mean",
    "columns": ["precio", "cantidad"],
    "data": [[1, 2], [3, 4], [5, 6]]
  }
}
```

**Variante B — Multipart form (CSV adjunto):**

```
Content-Type: multipart/form-data
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `job_type` | string (form field) | Sí | `"data-processing"` |
| `params` | string JSON (form field) | Sí | `{"operation":"mean","columns":["precio"]}` |
| `file` | UploadFile | Sí | Archivo CSV. Max 10 MB. |

**Lógica de splitting:** El servicio lee el CSV, lo divide en chunks de ~500 filas cada uno. Para N filas totales, se crean `ceil(N / 500)` chunks. El reward total del job se fija en `0.10 CC × total_chunks`.

**Response 201 — Job creado:**

```json
{
  "id": "job-uuid-1",
  "client_id": "550e8400-...",
  "job_type": "data-processing",
  "status": "processing",
  "params": {
    "operation": "mean",
    "columns": ["precio", "cantidad"]
  },
  "total_chunks": 4,
  "completed_chunks": 0,
  "reward_total": 0.40,
  "result": null,
  "created_at": "2026-06-07T10:00:00Z",
  "completed_at": null,
  "progress": 0.0
}
```

El status del job pasa por `pending` → `splitting` → `processing` antes de devolver la respuesta. El cliente recibe el job ya en `processing` con sus chunks creados.

**Response 400 — Tipo de job no soportado:**

```json
{ "detail": "Tipo de job no soportado: transcription" }
```

**Response 400 — CSV vacío o sin columnas válidas:**

```json
{ "detail": "El archivo CSV no contiene datos válidos" }
```

**Response 413 — Archivo demasiado grande:**

```json
{ "detail": "El archivo CSV no puede superar 10 MB" }
```

**Response 422 — Validación de campos fallida.**

---

#### `GET /jobs` [AUTH]

Lista todos los jobs del proveedor autenticado (como cliente), ordenados por `created_at DESC`.

**Query parameters:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `status` | string | No | Filtra por estado. Ej: `processing`, `completed`. |

**Response 200:**

```json
{
  "count": 2,
  "jobs": [
    {
      "id": "job-uuid-1",
      "client_id": "550e8400-...",
      "job_type": "data-processing",
      "status": "processing",
      "params": {"operation": "mean", "columns": ["precio"]},
      "total_chunks": 4,
      "completed_chunks": 2,
      "reward_total": 0.40,
      "result": null,
      "created_at": "2026-06-07T10:00:00Z",
      "completed_at": null,
      "progress": 50.0
    }
  ]
}
```

**Response 200 — Sin jobs:**

```json
{ "count": 0, "jobs": [] }
```

---

#### `GET /jobs/{job_id}` [AUTH]

Detalle de un job con progreso real en tiempo de consulta.

**Path parameter:** `job_id` (UUID)

**Response 200:**

```json
{
  "id": "job-uuid-1",
  "client_id": "550e8400-...",
  "job_type": "data-processing",
  "status": "processing",
  "params": {"operation": "mean", "columns": ["precio", "cantidad"]},
  "total_chunks": 4,
  "completed_chunks": 2,
  "reward_total": 0.40,
  "result": null,
  "created_at": "2026-06-07T10:00:00Z",
  "completed_at": null,
  "progress": 50.0
}
```

El campo `progress` = `completed_chunks / total_chunks × 100` (redondeado a 1 decimal). Si `total_chunks = 0`, `progress = 0.0`.

**Response 403 — El job no pertenece al proveedor autenticado:**

```json
{ "detail": "No tienes permiso para realizar esta acción" }
```

**Response 404 — Job no encontrado:**

```json
{ "detail": "Job no encontrado" }
```

---

#### `GET /jobs/{job_id}/result` [AUTH]

Devuelve el resultado consolidado del job. Solo disponible cuando `status = 'completed'`.

**Path parameter:** `job_id` (UUID)

**Response 200 — Job completado:**

```json
{
  "id": "job-uuid-1",
  "status": "completed",
  "result": {
    "operation": "mean",
    "columns": {
      "precio": 3.0,
      "cantidad": 4.0
    }
  },
  "total_chunks": 4,
  "completed_chunks": 4,
  "completed_at": "2026-06-07T10:05:00Z"
}
```

**Response 400 — Job aún no completado:**

```json
{ "detail": "El job aún no ha sido completado (estado actual: processing)" }
```

**Response 403 — El job no pertenece al proveedor autenticado:**

```json
{ "detail": "No tienes permiso para realizar esta acción" }
```

**Response 404 — Job no encontrado:**

```json
{ "detail": "Job no encontrado" }
```

---

### 6.4 Endpoints del Router `/work` (lado worker)

**Prefijo registrado en `app/main.py`:** `/work`
**Módulo:** `app/routers/work.py`
**Auth:** Todos los endpoints requieren `[AUTH]` (Bearer JWT del proveedor/worker).

---

#### `POST /work/claim` [AUTH]

El worker solicita hasta `max_chunks` chunks pendientes para procesar. La asignación es **atómica** (no puede haber dos workers reclamando el mismo chunk simultáneamente).

**Lógica de claim atómico:** Se usa psycopg2 con una query `UPDATE ... WHERE ... RETURNING` envuelta en `BEGIN`/`COMMIT`. La condición de selección garantiza que solo se asignan chunks donde el proveedor autenticado no haya entregado resultado aún:

```sql
-- Ejecutado via psycopg2 con BEGIN explícito:
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
SET status = 'assigned',
    assigned_to = %(provider_id)s,
    attempts = attempts + 1
FROM candidates
WHERE chunks.id = candidates.id
RETURNING chunks.id, chunks.job_id, chunks.chunk_index,
          chunks.payload, chunks.replicas_needed;
```

`FOR UPDATE SKIP LOCKED` garantiza que dos workers concurrentes no reclamen el mismo chunk. No bloquea; el segundo worker simplemente recibe el siguiente chunk disponible.

> **Nota v3:** la query mostrada arriba es la versión original (pre-v3). Desde la corrección de estabilidad v3, `claim_chunks_atomic` ejecuta un paso adicional de reclamo por TTL antes de esta query (y añade `assigned_at = now()` a este UPDATE) y devuelve además los `job_id` de cualquier chunk rechazado por exceder `MAX_CHUNK_ATTEMPTS`. El request/response de este endpoint no cambia. Ver el diseño completo y la razón de cada cambio en `docs/04-arquitectura.md` §14.2.

**Request body:**

```json
{
  "max_chunks": 3
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `max_chunks` | integer | Sí | ge=1, le=10. Cuántos chunks reclamar en este ciclo. |

**Response 200 — Chunks reclamados:**

```json
{
  "chunks": [
    {
      "chunk_id": "chunk-uuid-1",
      "job_id": "job-uuid-1",
      "chunk_index": 0,
      "job_type": "data-processing",
      "payload": {
        "rows": [[1, "A"], [2, "B"]],
        "columns": ["precio", "categoria"]
      }
    },
    {
      "chunk_id": "chunk-uuid-2",
      "job_id": "job-uuid-1",
      "chunk_index": 1,
      "job_type": "data-processing",
      "payload": {
        "rows": [[3, "C"], [4, "D"]],
        "columns": ["precio", "categoria"]
      }
    }
  ]
}
```

**Response 200 — No hay chunks disponibles:**

```json
{ "chunks": [] }
```

El worker interpreta una lista vacía como "nada que procesar ahora" y espera antes del próximo polling.

**Response 422 — Validación de body fallida (ej. max_chunks = 0).**

**Response 429 — Límite de reclamos por proveedor excedido (30/minuto, ver `docs/04-arquitectura.md` §15.1):**

```json
{ "detail": "Demasiadas peticiones. Inténtalo de nuevo en unos instantes." }
```

Cabecera de respuesta: `Retry-After: 60`. Identidad del bucket: `provider_id` del JWT, no la IP (varios workers legítimos pueden compartir IP/NAT).

---

#### `POST /work/{chunk_id}/submit` [AUTH]

El worker entrega el resultado de un chunk procesado. El servicio ejecuta la validación por consenso y, si el chunk se valida, actualiza el job y lanza el pago.

**Path parameter:** `chunk_id` (UUID)

**Request body:**

```json
{
  "result": {
    "precio_mean": 3.14,
    "cantidad_mean": 42.0
  },
  "duration_ms": 1250
}
```

| Campo | Tipo | Requerido | Validación |
|-------|------|-----------|------------|
| `result` | object | Sí | Cualquier objeto JSON no nulo. |
| `duration_ms` | integer | Sí | gt=0. Tiempo real de cómputo en ms. |

**Response 200 — Resultado aceptado, consenso pendiente (solo 1 réplica entregada de 2 necesarias):**

```json
{
  "chunk_result_id": "cr-uuid-1",
  "chunk_id": "chunk-uuid-1",
  "status": "assigned",
  "message": "Resultado recibido. Esperando segunda réplica para validar."
}
```

**Response 200 — Resultado aceptado, chunk validado por consenso (2 réplicas coinciden):**

```json
{
  "chunk_result_id": "cr-uuid-2",
  "chunk_id": "chunk-uuid-1",
  "status": "done",
  "message": "Chunk validado. Recompensa acreditada."
}
```

**Response 200 — Resultado aceptado, desacuerdo entre réplicas (necesita 3.er desempate):**

```json
{
  "chunk_result_id": "cr-uuid-2",
  "chunk_id": "chunk-uuid-1",
  "status": "assigned",
  "message": "Desacuerdo entre réplicas. Se asignará un tercer proveedor para desempate."
}
```

En este caso el servicio cambia el chunk de vuelta a `pending` para que otro worker lo reclame.

**Response 400 — El proveedor no tiene este chunk asignado:**

```json
{ "detail": "No tienes este chunk asignado" }
```

**Response 400 — Ya entregaste un resultado para este chunk:**

```json
{ "detail": "Ya has entregado un resultado para este chunk" }
```

**Response 404 — Chunk no encontrado:**

```json
{ "detail": "Chunk no encontrado" }
```

**Response 429 — Límite de submits por proveedor excedido (60/minuto, ver `docs/04-arquitectura.md` §15.1):**

```json
{ "detail": "Demasiadas peticiones. Inténtalo de nuevo en unos instantes." }
```

Cabecera de respuesta: `Retry-After: 60`.

---

### 6.5 Resumen de Endpoints Compute

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/jobs` | Sí | Crear job (cliente) |
| `GET` | `/jobs` | Sí | Listar mis jobs (cliente) |
| `GET` | `/jobs/{job_id}` | Sí | Detalle con progreso real (cliente) |
| `GET` | `/jobs/{job_id}/result` | Sí | Resultado consolidado (cliente) |
| `POST` | `/work/claim` | Sí | Reclamar chunks (worker) |
| `POST` | `/work/{chunk_id}/submit` | Sí | Entregar resultado (worker) |

---

### 6.6 Fórmulas de Negocio — Compute

#### Reward por chunk

```
reward_per_chunk = job.reward_total / job.total_chunks
```

Solo se paga por resultados con `is_valid = true`. Un resultado marcado `is_valid = false` no genera pago y aplica penalización de Trust Score (`accuracy -= 5`, usando `trust_score.update_accuracy_on_fail`).

#### Progreso del job

```
progress = (completed_chunks / total_chunks) × 100
```

Si `total_chunks = 0`, `progress = 0.0`. Se redondea a 1 decimal.

#### Chunk splitting para CSV

```
chunk_size = 500 filas
total_chunks = ceil(total_rows / chunk_size)
chunk[i].payload = {
  "rows": rows[i*500 : (i+1)*500],
  "columns": csv_headers
}
```

#### Actualización de Trust Score por resultado de chunk

| Evento | `accuracy` | `response_time_score` |
|--------|------------|----------------------|
| Resultado válido (`is_valid=true`) | `min(accuracy + 2, 100)` | sin cambio |
| Resultado inválido (`is_valid=false`) | `max(accuracy - 5, 0)` | sin cambio |

Usa directamente las funciones `update_accuracy_on_complete` y `update_accuracy_on_fail` de `app/services/trust_score.py`.
