# Co-Computing — Code Review Report

**Fecha:** 2026-06-06
**Revisor:** Code Reviewer Senior
**Rama revisada:** main
**Scope:** backend/, frontend/, migrations/, tests/ + contrato de API docs/04-api-contracts.md

---

## Índice

1. [Hallazgos CRÍTICOS](#1-críticos)
2. [Hallazgos ALTOS](#2-altos)
3. [Hallazgos MEDIOS](#3-medios)
4. [Hallazgos BAJOS](#4-bajos)
5. [Resumen ejecutivo](#5-resumen-ejecutivo)
6. [Handoff al Security Auditor](#6-handoff-al-security-auditor)

---

## 1. CRÍTICOS

### C-01 — Race condition en retiro de fondos (TOCTOU)

**Archivo:** `backend/app/services/wallet_service.py`, líneas 62–78
**Archivo relacionado:** `backend/app/db/queries/wallet_queries.py`, líneas 113–139

**Descripción:**
La función `process_withdrawal` realiza la validación del saldo (`amount > available`) en Python usando el valor devuelto por `get_wallet_by_provider_id`, y luego delega la actualización a `update_wallet_on_withdraw` que hace exactamente lo mismo (vuelve a leer el saldo con `get_wallet_by_provider_id` y después hace el UPDATE). Entre ambas lecturas y el UPDATE no hay ningún mecanismo de bloqueo. Si dos requests de retiro llegan simultáneamente para el mismo proveedor, ambas pueden pasar la validación de saldo suficiente y ambas ejecutar el descuento, llevando el `available_balance` a negativo, violando la regla de negocio y potencialmente la constraint de la BD (`CHECK (available_balance >= 0)`).

**Contraste con esquema:** `migrations/001_schema.sql` línea 179 incluye `CONSTRAINT wallets_available_balance_non_negative CHECK (available_balance >= 0)` que actuará como red de seguridad a nivel de BD, pero solo después del fallo, haciendo que la request llegue a un error 500 en lugar de un 400 controlado; además la constraint no previene que el primer retiro ya haya deducido el saldo antes de que el segundo falle.

**Impacto:** Pérdida económica real. Un proveedor puede retirar más CC de los disponibles mediante solicitudes simultáneas.

**Fix sugerido:**
Reemplazar el UPDATE de dos pasos por un UPDATE condicional atómico en SQL, similar al patrón ya usado en `decrement_slots_atomic`:
```sql
UPDATE wallets
SET available_balance  = available_balance - %s,
    total_withdrawn    = total_withdrawn + %s,
    updated_at         = now()
WHERE provider_id = %s
  AND available_balance >= %s
RETURNING available_balance
```
Si el `RETURNING` devuelve una fila, el retiro fue exitoso. Si no, el saldo era insuficiente. Eliminar la doble lectura de la cartera y la validación en Python.

---

### C-02 — Doble escritura redundante en el assignment al completar/fallar tarea

**Archivo:** `backend/app/services/task_lifecycle.py`, líneas 134–141 y 204–209 (complete_task); líneas 252–257 y 304–309 (fail_task)

**Descripción:**
En `complete_task`, el assignment se actualiza dos veces con `update_assignment_status`: una primera vez para poner `status=completada`, `completed_at` y `reward_paid` (líneas 134–141), y una segunda vez para añadir únicamente el `trust_delta` (líneas 204–209). Esto introduce una ventana de tiempo donde el registro existe en BD con `reward_paid` pero sin `trust_delta`. Si el proceso falla entre las dos escrituras (error de red, crash), la fila queda en estado inconsistente. El mismo patrón se repite en `fail_task`.

**Impacto:** Inconsistencia de datos: assignments con `reward_paid` correctamente seteado pero `trust_delta = null`, aunque el dinero ya fue acreditado. Dificulta auditorías y reconciliación.

**Fix sugerido:**
Calcular el `trust_delta` antes de hacer cualquier escritura a la BD y realizar una única llamada a `update_assignment_status` con todos los campos a la vez: `status`, `completed_at`, `reward_paid` (o null en fail), y `trust_delta`. Mover el cálculo del trust score al bloque anterior a la primera escritura.

---

### C-03 — `update_wallet_on_task_complete` no es atómica: leer-modificar-escribir desprotegido

**Archivo:** `backend/app/db/queries/wallet_queries.py`, líneas 84–110

**Descripción:**
`update_wallet_on_task_complete` lee el saldo actual (`get_wallet_by_provider_id`, round-trip 1), calcula los nuevos valores en Python, y luego hace el UPDATE (round-trip 2). No hay transacción, ni bloqueo optimista, ni UPDATE condicional. Si dos tareas del mismo proveedor se completan concurrentemente, ambas pueden leer el mismo `available_balance` inicial y ambas escribir incrementos basados en ese valor, perdiendo uno de los créditos.

**Impacto:** Pérdida de recompensas para el proveedor o inconsistencia en `total_earned`.

**Fix sugerido:**
Usar un UPDATE con aritmética SQL directa en lugar de leer + calcular + escribir:
```sql
UPDATE wallets
SET available_balance = available_balance + %s,
    total_earned      = total_earned + %s,
    updated_at        = now()
WHERE provider_id = %s
RETURNING available_balance, total_earned
```
Esto es atómico por la naturaleza del motor PostgreSQL.

---

### C-04 — `get_provider_by_id` duplicado en dos módulos de queries distintos

**Archivo 1:** `backend/app/db/queries/auth_queries.py`, líneas 25–37
**Archivo 2:** `backend/app/db/queries/profile_queries.py`, líneas 9–21

**Descripción:**
La función `get_provider_by_id` con implementación idéntica está definida en dos módulos. El router de `dependencies.py` importa de `auth_queries`, mientras que `task_lifecycle.py` y `profile_queries.py` tienen su propia versión. Ambas emiten exactamente el mismo SELECT.

**Impacto:** Si se necesita cambiar el comportamiento (añadir campos, cambiar la tabla), hay que actualizar dos sitios. El riesgo de divergencia ya existe: si se añaden nuevos campos al SELECT de uno pero no del otro, los datos que llegan a `get_current_provider` podrán diferir de los que llegan a `get_stats`.

**Fix sugerido:**
Centralizar `get_provider_by_id` en un único módulo (p.ej. `backend/app/db/queries/provider_queries.py`) y hacer que ambos módulos lo importen desde allí. Eliminar la copia de `auth_queries.py`.

---

## 2. ALTOS

### A-01 — Token almacenado en localStorage, expuesto a XSS

**Archivo:** `frontend/src/store/authStore.ts`, líneas 35–37; `frontend/src/api/client.ts`, línea 16

**Descripción:**
El JWT de sesión se guarda en `localStorage` con la clave `co_computing_token`. El interceptor de Axios lo lee también desde `localStorage`. Cualquier script inyectado mediante XSS puede leer este token y suplantar la identidad del usuario. El proyecto usa React con Vite, y aunque el riesgo de XSS en React es menor por el escaping automático, no es nulo (dependencias de terceros, campos que renderizan HTML, etc.).

**Impacto:** Robo de sesión completo si existe cualquier vector XSS.

**Fix sugerido:**
Mover el almacenamiento del token a una cookie `HttpOnly; Secure; SameSite=Strict`. El backend debe leer el token desde la cookie en lugar del header `Authorization`. El provider (datos no sensibles) puede seguir en `localStorage` o en estado en memoria de Zustand. Valorar si la arquitectura actual con FastAPI permite cookies fácilmente (requiere adaptar el middleware CORS con `allow_credentials=True`, ya presente).

---

### A-02 — Ausencia de rate limiting en endpoints de autenticación

**Archivo:** `backend/app/routers/auth.py` (POST /auth/register, POST /auth/login)
**Archivo:** `backend/app/main.py`

**Descripción:**
No existe ningún mecanismo de rate limiting ni throttling en los endpoints de login y registro. Un atacante puede realizar ataques de fuerza bruta sobre el endpoint `/auth/login` sin ningún obstáculo a nivel de aplicación. El proyecto no menciona ningún WAF o proxy que implemente esta protección externamente.

**Impacto:** Ataques de fuerza bruta sobre contraseñas de usuarios existentes. El hecho de que bcrypt con 12 rounds ralentiza las verificaciones individuales no es suficiente frente a ataques distribuidos o cuando el atacante conoce el email objetivo.

**Fix sugerido:**
Añadir `slowapi` (compatible con FastAPI) para limitar intentos de login a, por ejemplo, 5 por minuto por IP. En registro, 3 por hora por IP. Ejemplo:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest) -> TokenResponse:
    ...
```

---

### A-03 — Sin validación de UUID en path parameters del backend

**Archivo:** `backend/app/routers/tasks.py`, líneas 186, 218, 244, 259, 274
**Archivo:** `backend/app/routers/tasks.py`, línea 109

**Descripción:**
Los path parameters `task_id` y `assignment_id` se declaran como `str` sin ninguna validación de formato UUID. Aunque FastAPI no valida el formato automáticamente con `str`, se puede pasar cualquier cadena arbitraria que llegará directamente a la BD. Las queries de Supabase SDK con `.eq("id", task_id)` pasan ese valor a PostgreSQL. Si `task_id` no es un UUID válido, PostgreSQL lanzará un error de tipo (cast error) que se convierte en un 500.

**Impacto:** Cualquier URL malformada como `/tasks/../../../../etc/passwd` (aunque filtrada por la BD) produce un 500 en lugar de un 404. Puede filtrar información de stack trace si el handler genérico de excepciones falla.

**Fix sugerido:**
Cambiar la firma a:
```python
from uuid import UUID
task_id: UUID = Path(...)
```
FastAPI validará el formato y devolverá 422 automáticamente. Al pasar a las queries, usar `str(task_id)`.

---

### A-04 — accept_task no verifica que la tarea esté en estado "disponible"

**Archivo:** `backend/app/services/task_lifecycle.py`, líneas 29–55

**Descripción:**
`accept_task` verifica que la tarea existe y que quedan slots (`decrement_slots_atomic`), pero no verifica que `task.status == "disponible"`. Una tarea con `status = "en_progreso"` o `"completada"` pero con `slots_left > 0` (por ejemplo debido a un bug previo) podría ser aceptada. El `decrement_slots_atomic` solo comprueba `slots_left > 0`, no el estado de la tarea.

**Impacto:** Un proveedor podría aceptar una tarea que ya no debería estar disponible.

**Fix sugerido:**
Añadir validación explícita después de recuperar la tarea:
```python
if task["status"] != "disponible":
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Esta tarea ya no está disponible",
    )
```

---

### A-05 — `_parse_datetime` en `task_lifecycle.py` silencia `started_at = None` con `datetime.now()`

**Archivo:** `backend/app/services/task_lifecycle.py`, líneas 323–334

**Descripción:**
La función `_parse_datetime` devuelve `datetime.now(timezone.utc)` cuando `value is None`. Esta función se usa para parsear `started_at` en `complete_task` y `fail_task`. Si por alguna razón `started_at` es `None` (la tarea fue completada sin haberse iniciado correctamente, o hubo un bug previo), la función calcula el `response_time_score` basándose en el timestamp actual como si fuera el momento de inicio, lo cual es silenciosamente incorrecto.

**Impacto:** Cálculo erróneo del `response_time_score` cuando `started_at` es null, produciendo actualizaciones de Trust Score incorrectas sin ningún error que lo indique.

**Fix sugerido:**
Lanzar una excepción explícita si `started_at` es None en estos contextos:
```python
if assignment["started_at"] is None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="La tarea no ha sido iniciada",
    )
```
O bien, si el caso es legítimo, documentar y tratar de forma separada sin usar `now()` silenciosamente.

---

### A-06 — Doble conexión psycopg2 por cada petición de progreso (polling cada 3s)

**Archivo:** `backend/app/db/queries/task_queries.py`, líneas 217–244

**Descripción:**
`get_assignment_with_task` abre una nueva conexión `psycopg2.connect(...)` por cada llamada. El endpoint `/tasks/assignments/{id}/progress` está diseñado para polling cada 3 segundos. Cada poll abre y cierra una conexión directa a PostgreSQL sin pooling. Con múltiples usuarios en procesamiento simultáneo, esto puede agotar las conexiones disponibles en el servidor de BD.

De forma similar, `decrement_slots_atomic` y `get_provider_assignments_history` también abren conexiones directas sin pool.

**Impacto:** Agotamiento de conexiones PostgreSQL bajo carga moderada. Latencia creciente por overhead de establecimiento de conexión TCP + TLS + autenticación.

**Fix sugerido:**
Implementar un pool de conexiones con `psycopg2.pool.ThreadedConnectionPool` o migrar a `asyncpg` con un pool. Alternativamente, mover las queries join a la Supabase SDK usando `.select("*, tasks(*)")` para evitar psycopg2 completamente en estos casos simples.

---

### A-07 — `password_min_length` validator redundante en `RegisterRequest`

**Archivo:** `backend/app/models/auth.py`, líneas 15–19

**Descripción:**
El campo `password` ya tiene `Field(..., min_length=8)`, que Pydantic v2 valida automáticamente. Sin embargo, se añade además un `@field_validator("password")` que vuelve a comprobar `len(v) < 8`. Esta segunda validación es completamente redundante: si la validación de `Field(min_length=8)` pasa, el `@field_validator` nunca verá una cadena corta.

**Impacto:** Código muerto que no produce ningún efecto pero induce a confusión.

**Fix sugerido:**
Eliminar el `@field_validator("password_min_length")` por completo. La validación de `Field(min_length=8)` es suficiente.

---

## 3. MEDIOS

### M-01 — `conftest.py` usa IDs de UUID fijos globales (module-level), no por test

**Archivo:** `backend/tests/conftest.py`, líneas 23–25

**Descripción:**
`PROVIDER_ID`, `TASK_ID` y `ASSIGNMENT_ID` son constantes de módulo generadas una sola vez al importar el módulo. Todos los tests de la misma sesión de pytest comparten el mismo UUID. Aunque con mocking esto no es un problema inmediato, si en el futuro se añaden tests que usen la BD real, compartir IDs entre tests puede causar interferencias.

**Fix sugerido:**
Convertir en fixtures de pytest con scope apropiado:
```python
@pytest.fixture
def provider_id() -> str:
    return str(uuid.uuid4())
```

---

### M-02 — `RegisterRequest` y `LoginRequest` no sanitizan el email (mayúsculas/espacios)

**Archivo:** `backend/app/models/auth.py`, líneas 6–13 y 22–25

**Descripción:**
Los modelos aceptan el email tal como viene del cliente. Si un usuario se registra con `" Ana@Example.COM "` y luego intenta login con `"ana@example.com"`, la búsqueda `get_provider_by_email` fallará porque el texto exacto no coincide (aunque la constraint UNIQUE en PostgreSQL sí es case-insensitive en la mayoría de configuraciones, el `.eq("email", email)` de Supabase SDK es case-sensitive por defecto).

**Fix sugerido:**
Añadir un `@field_validator("email")` en ambos modelos que normalice:
```python
return v.strip().lower()
```

---

### M-03 — La migración 001 tiene un comentario incorrecto sobre el orden de ejecución de triggers

**Archivo:** `migrations/001_schema.sql`, líneas 349–360

**Descripción:**
El comentario afirma que "PostgreSQL ordena los triggers BEFORE por nombre alfabéticamente" y que `trg_recalculate_trust_score` se ejecuta antes que `trg_providers_updated_at` porque la letra "r" es menor alfabéticamente que... espera, `trg_providers_updated_at` (p) < `trg_recalculate_trust_score` (r) en orden alfabético, por lo que el trigger `trg_providers_updated_at` (set_updated_at) se ejecutaría PRIMERO, y después `trg_recalculate_trust_score`.

El problema es que el comentario dice que el orden es correcto, pero si `set_updated_at` se ejecuta antes, `updated_at` queda bien, y luego `recalculate_trust_score` cambia `NEW.trust_score` y `NEW.rank` pero ya no afecta `updated_at` (ambos son BEFORE, así que los cambios en NEW se acumulan). En este caso concreto no hay un bug funcional porque ambos triggers modifican campos distintos (updated_at vs trust_score/rank), pero la explicación del comentario sobre el orden alfabético es inversa a la correcta. Esto puede inducir a confusión futura.

**Fix sugerido:**
Corregir el comentario para reflejar el orden real: `trg_providers_updated_at` (p < r) se ejecuta antes que `trg_recalculate_trust_score`. Confirmar que ambos triggers coexisten correctamente (sí lo hacen, pues modifican campos distintos en NEW).

---

### M-04 — `build_rank_info` puede lanzar `KeyError` con rank inválido

**Archivo:** `backend/app/services/trust_score.py`, líneas 60–86

**Descripción:**
`build_rank_info` accede a `RANK_BOUNDARIES[rank]` sin verificar que `rank` sea una clave válida. Si el campo `rank` en la BD contiene un valor inesperado (bug de data migration, inserción manual), se lanzará un `KeyError` que el handler genérico convertirá en 500. La función `get_rank` siempre devuelve uno de los cuatro valores válidos, pero `build_rank_info` también es llamada con el valor que viene directamente de la BD (`provider["rank"]`).

**Fix sugerido:**
Añadir validación al inicio:
```python
if rank not in RANK_BOUNDARIES:
    rank = "nuevo"  # fallback seguro
```
O bien lanzar un error controlado con mensaje descriptivo.

---

### M-05 — `useProgress` navega automáticamente al dashboard cuando status es terminal, incluso si el usuario está completando manualmente

**Archivo:** `frontend/src/hooks/useProgress.ts`, líneas 44–58

**Descripción:**
El hook detecta `status === 'completada'` o `status === 'fallida'` y redirige automáticamente al dashboard. Sin embargo, en `ProcessingPage.tsx` el usuario puede estar en medio del flujo de confirmación de completar (con el modal abierto, esperando confirmar). Si el polling devuelve el estado terminal justo después de que el usuario haya pulsado "Confirmar y cobrar" pero antes de que `completeTask` haya terminado, el hook puede navegar al dashboard mientras la petición de complete aún está en vuelo, resultando en una UI inconsistente.

**Fix sugerido:**
Añadir una bandera `isConfirming` al hook o al componente, y no redirigir automáticamente si hay una acción manual en curso:
```typescript
if ((data.status === 'completada' || data.status === 'fallida') && !isConfirming) {
  navigate('/dashboard', ...)
}
```

---

### M-06 — `handleToggleOnline` en ProfilePage silencia todos los errores

**Archivo:** `frontend/src/pages/ProfilePage.tsx`, líneas 101–113

**Descripción:**
El bloque `catch` de `handleToggleOnline` está vacío (comentario `// silencioso`). Si el toggle falla por error de red o 500, el estado local de la UI (el toggle visual) puede no actualizarse mientras que el backend mantiene el estado anterior, mostrando al usuario un estado visual incorrecto.

**Fix sugerido:**
Revertir el estado local del toggle en caso de error y mostrar un mensaje toast o alert:
```typescript
} catch {
  setStats((prev) => prev ? { ...prev, is_online: !prev.is_online } : prev)
  // mostrar notificación de error
}
```

---

### M-07 — Ausencia de límite superior en las conexiones psycopg2 para `get_provider_assignments_history`

**Archivo:** `backend/app/db/queries/task_queries.py`, líneas 136–163

**Descripción:**
`get_provider_assignments_history` hace un SELECT sin LIMIT sobre `task_assignments JOIN tasks`. Un proveedor muy activo con miles de asignaciones recibirá todas en una sola respuesta sin paginación, consumiendo memoria y tiempo de serialización.

**Contrate con el contrato de API:** `docs/04-api-contracts.md` sección 2.2 dice "ordenadas por fecha de creación descendente" sin mencionar límite. El endpoint `GET /tasks/my/history` en el dashboard solo muestra las 5 primeras (frontend limita con `.slice(0, 5)`), pero la query trae todo.

**Fix sugerido:**
Añadir `LIMIT 200` a la query SQL como cota de seguridad, o implementar paginación completa en el endpoint. La limitación de 5 en el frontend es frágil.

---

### M-08 — Seed inserta transacciones con `task_id = NULL` para pagos de tarea

**Archivo:** `migrations/003_seed.sql`, líneas 116–128

**Descripción:**
La primera transacción de seed es de tipo `pago_tarea` pero tiene `task_id = NULL`. El contrato de datos (`docs/04-api-contracts.md`, sección 1.5) especifica que `task_id` es nulo solo para retiros y bonos. Una transacción de `pago_tarea` con `task_id = NULL` viola la semántica del modelo de datos y puede confundir a herramientas de análisis o dashboards futuros.

**Fix sugerido:**
Si el seed es puramente ilustrativo, usar un UUID de tarea existente del propio seed (p.ej. `aaaaaaaa-0001-0001-0001-000000000001`). Si no se quiere vincular, cambiar el tipo a `bonus` o documentar la excepción explícitamente.

---

### M-09 — `update_assignment_status` no valida la transición de estado

**Archivo:** `backend/app/db/queries/task_queries.py`, líneas 182–202

**Descripción:**
`update_assignment_status` es una función genérica que acepta cualquier valor de `status` y lo escribe sin validar que la transición sea legal (p.ej., de `completada` a `aceptada` es inválido). La validación de transiciones existe en `task_lifecycle.py`, pero si alguien llama a `update_assignment_status` directamente desde otro contexto futuro, puede dejar la BD en estado inválido.

**Fix sugerido:**
Añadir un diccionario de transiciones permitidas en la capa de queries o de servicio, y validar antes de ejecutar el UPDATE. Alternativamente, añadir una constraint de check en la BD que limite las transiciones (más complejo en PostgreSQL standard, requeriría triggers).

---

## 4. BAJOS

### B-01 — `DashboardPage` no cancela las peticiones en vuelo si el componente se desmonta

**Archivo:** `frontend/src/pages/DashboardPage.tsx`, líneas 60–72

**Descripción:**
La función `loadData` lanza dos peticiones con `Promise.all` pero no usa `AbortController`. Si el usuario navega fuera del dashboard antes de que las peticiones terminen, React mostrará una advertencia de "setState on unmounted component" (en React 18 ya no es un error pero sí una posible fuga de estado).

**Fix sugerido:**
Usar `AbortController` y pasar el signal a axios, o mover la lógica a un custom hook que gestione el ciclo de vida.

---

### B-02 — Validación de `min_reward = 0` produce error 422 en lugar del 400 documentado

**Archivo:** `backend/app/routers/tasks.py`, línea 41 — `min_reward: float | None = Query(default=None, gt=0)`
**Contrato:** `docs/04-api-contracts.md`, línea 416: "Response 400 — Valor de filtro inválido (ej. min_reward negativa)"

**Descripción:**
El contrato de API especifica que un `min_reward` inválido devuelve 400. Sin embargo, la validación de `gt=0` en el Query param de FastAPI devuelve automáticamente 422 (Pydantic validation error). El test `test_list_tasks_invalid_min_reward` en `test_tasks.py` (línea 60–63) espera 422, lo que es coherente con la implementación real, pero incoherente con el contrato.

**Impacto:** Bajo. El contrato está mal documentado respecto a este caso concreto.

**Fix sugerido:**
Actualizar `docs/04-api-contracts.md` para indicar que errores de validación de query params devuelven 422, no 400.

---

### B-03 — LoginPage y RegisterPage duplican la estructura de cabecera pública

**Archivo:** `frontend/src/pages/LoginPage.tsx`, líneas 54–62
**Archivo:** `frontend/src/pages/RegisterPage.tsx`, líneas 61–69

**Descripción:**
El JSX del header público (logo BoltIcon + texto "Co-Computing") está duplicado byte a byte entre ambas páginas. También el bloque del logo dentro del card (líneas 66–71 en Login, 74–79 en Register).

**Fix sugerido:**
Extraer un componente `PublicHeader` y un componente `PublicCard` o `AuthLayout` que encapsule la estructura compartida.

---

### B-04 — `extractErrorMessage` en `client.ts` maneja el caso 401 que ya está gestionado por el interceptor

**Archivo:** `frontend/src/api/client.ts`, líneas 45–59

**Descripción:**
El interceptor de respuesta (líneas 26–40) ya gestiona el 401 limpiando la sesión y disparando el evento de sesión expirada. La función `extractErrorMessage` tiene además un caso explícito para 401 (línea 52). Esto significa que ante un 401, tanto el interceptor como el extractor de mensajes actúan, pudiendo producir dos comportamientos solapados (redirección + mensaje de error en UI).

**Fix sugerido:**
Eliminar el caso `status === 401` de `extractErrorMessage` ya que el interceptor se encarga de ello de forma global.

---

### B-05 — `useAuth.handleRegister` hace login inmediato pero el Provider devuelto por register no es el del login

**Archivo:** `frontend/src/hooks/useAuth.ts`, líneas 20–32

**Descripción:**
`handleRegister` llama a `authApi.register(data)` (que devuelve `ProviderPublic` sin campos extendidos), y luego hace `authApi.login(...)` para obtener el token y el Provider con todos los campos. El objeto `provider` de la primera llamada se guarda en la variable local pero se descarta. Solo `loginResponse.provider` se usa para la sesión. Esto es correcto funcionalmente pero confuso en la firma de retorno: `handleRegister` retorna `provider` (de register, sin token), que ningún caller parece usar.

**Fix sugerido:**
Cambiar la firma de `handleRegister` a `Promise<void>` en lugar de `Promise<Provider>`, ya que el valor de retorno no es consumido en ningún lugar del código visible.

---

### B-06 — `tasks_seed.sql` referenciado en `backend/app/seed/` pero no hay evidencia de su uso en CI

**Archivo:** `backend/app/seed/tasks_seed.sql` (encontrado en Glob)
**Archivo:** `backend/app/seed/seed.py`

**Descripción:**
Existe un directorio `backend/app/seed/` con un archivo SQL y un script Python de seed separados del directorio oficial `migrations/`. La relación entre estos archivos y las migraciones `migrations/003_seed.sql` no está documentada. Puede haber datos de seed duplicados o conflictivos.

**Fix sugerido:**
Revisar si `backend/app/seed/` está obsoleto y eliminarlo, o documentar explícitamente su propósito y cuándo debe ejecutarse respecto a las migraciones.

---

### B-07 — Constraint UNIQUE (`task_id, provider_id`) en `task_assignments` puede impedir re-aceptar tareas tras cancelación

**Archivo:** `migrations/001_schema.sql`, línea 213

**Descripción:**
La constraint `UNIQUE (task_id, provider_id)` es absoluta y no tiene condición parcial. Si un proveedor acepta una tarea y luego ésta se cancela (status = 'cancelada'), no podrá volver a aceptar la misma tarea en el futuro porque ya existe una fila con esa combinación (cancelada).

**Contrato de API:** `docs/04-api-contracts.md` línea 112: "la constraint se aplica solo si el status previo es terminal" — pero la constraint SQL no implementa esta lógica.

**Fix sugerido:**
Cambiar a una unique constraint parcial:
```sql
CREATE UNIQUE INDEX idx_task_assignments_active_unique
    ON task_assignments (task_id, provider_id)
    WHERE status IN ('aceptada', 'procesando');
```
Y eliminar la constraint `UNIQUE (task_id, provider_id)` absoluta.

---

### B-08 — `WalletPage` no valida que el `destination` sea un email válido cuando el método es PayPal

**Archivo:** `frontend/src/pages/WalletPage.tsx`, líneas 92–113

**Descripción:**
La validación del formulario de retiro solo comprueba que `destination` no esté vacío, independientemente del método. Cuando el método es `paypal`, el destino debería ser un email válido. El backend no hace esta validación tampoco: `destination: str = Field(..., min_length=1, max_length=200)` en `WithdrawRequest`.

**Impacto:** Un usuario puede enviar `"no-es-un-email"` como destino de PayPal. El retiro queda registrado con un destino inválido que no podrá procesarse.

**Fix sugerido:**
En el frontend, añadir validación de email cuando `withdrawMethod === 'paypal'`. En el backend, añadir validación condicional en `WithdrawRequest` con `@model_validator`.

---

## 5. Resumen ejecutivo

### Conteo por severidad

| Severidad | Cantidad | Hallazgos |
|-----------|----------|-----------|
| CRÍTICO   | 4        | C-01, C-02, C-03, C-04 |
| ALTO      | 7        | A-01 a A-07 |
| MEDIO     | 9        | M-01 a M-09 |
| BAJO      | 8        | B-01 a B-08 |
| **Total** | **28**   | |

### Evaluación general

**Calidad del código:** Buena estructura general. La separación de capas (routers → services → queries) es correcta y consistente. Los modelos Pydantic están bien definidos y la cobertura de tests con mocking es amplia.

**Problemas sistémicos identificados:**
1. El acceso a la BD mezcla el SDK de Supabase (para la mayoría de operaciones) con psycopg2 directo (para operaciones que requieren atomicidad). Esta mezcla es válida en concepto, pero las operaciones con psycopg2 abren conexiones sin pooling, lo que es un problema de escalabilidad importante dado que el endpoint de progreso se consulta con polling cada 3 segundos.

2. Los tres hallazgos críticos de concurrencia (C-01, C-02, C-03) tienen el mismo patrón raíz: operaciones de lectura-modificación-escritura sin atomicidad. El patrón correcto ya existe en el código para `decrement_slots_atomic` — hay que aplicarlo al resto de operaciones financieras.

3. La duplicación de `get_provider_by_id` (C-04) es deuda técnica que debe resolverse antes de añadir más funcionalidades.

**Cobertura de tests:** Los tests unitarios son de buena calidad y cubren los happy paths y principales errores de cada endpoint. No hay tests de integración ni tests de concurrencia que hubieran detectado C-01, C-02, C-03.

**Coherencia backend-frontend:** El contrato de API está bien seguido. El único punto de desacuerdo real es B-02 (422 vs 400 para `min_reward` inválido), que es una imprecisión en la documentación del contrato, no una incoherencia en la implementación.

---

## 6. Handoff al Security Auditor

El Security Auditor debe priorizar los siguientes puntos que tienen impacto directo en seguridad:

**Máxima prioridad:**

1. **C-01 — Race condition en retiros:** Un usuario malintencionado con dos sesiones paralelas puede retirar más fondos de los disponibles. Requiere prueba de explotación y fix urgente antes de cualquier despliegue con dinero real.

2. **A-01 — JWT en localStorage:** Revisar el vector XSS completo del frontend. Evaluar todas las librerías de terceros del `package.json`, cualquier uso de `dangerouslySetInnerHTML`, y cualquier contenido generado por usuarios que se renderice. Si se confirma que hay o puede haber XSS, el token en localStorage es un riesgo crítico.

3. **A-02 — Ausencia de rate limiting:** Confirmar si existe algún proxy inverso (Nginx, Cloudflare, etc.) que ya implemente rate limiting antes de que las peticiones lleguen a FastAPI. Si no existe ninguna capa de protección, este es un riesgo alto para producción.

**Alta prioridad:**

4. **A-03 — Path params sin validación UUID:** Aunque las queries de Supabase SDK probablemente manejen el error de tipo, evaluar si existe algún camino donde una cadena maliciosa pueda escapar al SDK y llegar a las queries psycopg2 crudas (en los tres módulos que usan psycopg2 con parámetros posicionales: `%s` — esto es seguro contra SQL injection, pero conviene confirmarlo explícitamente).

5. **002_rls.sql — RLS declarativamente inactivo para JWT propio:** El archivo reconoce explícitamente que las políticas de usuario (basadas en `auth.uid()`) no tienen efecto en el MVP porque se usa JWT HS256 propio. La seguridad de aislamiento entre proveedores depende 100% de la capa de FastAPI. El auditor debe verificar que todos los endpoints que acceden a datos de un proveedor comprueban efectivamente que el `provider_id` del recurso coincide con el `provider_id` del JWT. Verificar especialmente el endpoint de progreso (`/tasks/assignments/{id}/progress`) donde sí existe la comprobación explícita (línea 125 de `tasks.py`), y los endpoints de wallet/profile que acceden por `current_provider["id"]` (correcto).

6. **Seed en producción:** El archivo `migrations/003_seed.sql` inserta un proveedor demo con credenciales conocidas (`demo@co-computing.io` / `demo1234`). Verificar que este seed no se ejecuta en entornos de producción o que la cuenta demo se deshabilita/elimina antes del go-live.

7. **`supabase_service_role_key` en config:** Esta clave bypasea todo RLS. Verificar que el `.env` nunca se sube al repositorio (hay `.gitignore` y `.env.example`, confirmado), y que en el entorno de despliegue se gestiona como secret (no como variable de entorno plana en CI logs).
