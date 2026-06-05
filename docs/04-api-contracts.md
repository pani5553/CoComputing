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
