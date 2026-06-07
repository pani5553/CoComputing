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

---

## Revisión Feature Cómputo Real — 2026-06-07

**Revisor:** Code Reviewer Senior
**Scope:** feature/computo-real — archivos nuevos y modificados listados en el encargo
**Referencia:** `briefs/02-computo-real.md`

---

### Índice de hallazgos

| ID | Severidad | Resumen |
|----|-----------|---------|
| R2-C-01 | CRÍTICO | `JobListPage.tsx` no compila: `Link` y `Button` usados sin importar |
| R2-C-02 | CRÍTICO | Race condition en `update_wallet_on_task_complete` — mismo patrón no-atómico ya marcado como C-03 en revisión anterior, ahora usado por `credit_reward` |
| R2-C-03 | CRÍTICO | `consensus_service.py`: el bloque de pay+trust no es transaccional — si `credit_reward` tiene éxito pero `update_provider` falla, el pago queda acreditado y el trust sin actualizar |
| R2-A-01 | ALTO | `HTTP_413_REQUEST_ENTITY_TOO_LARGE` deprecado (QA bug #1 — NO corregido) |
| R2-A-02 | ALTO | `class Config` en `JobPublic` (QA bug #2 — NO corregido) |
| R2-A-03 | ALTO | Submit duplicado devuelve 400 en vez de 409 (QA bug #3 — NO corregido) |
| R2-A-04 | ALTO | US-38 CA-8: chunk con >5 intentos no se marca como `rejected` (QA bug #4 — NO implementado) |
| R2-A-05 | ALTO | `create_job_with_chunks` no es atómica: job se crea aunque falle la inserción de chunks |
| R2-A-06 | ALTO | `claim_chunks_atomic` sobrescribe `assigned_to` con el último reclamante pero el campo sólo admite un proveedor — el segundo reclamante de un chunk con `replicas_needed=2` pierde su assignment |
| R2-M-01 | MEDIO | `REWARD_PER_CHUNK` definido en tres módulos distintos |
| R2-M-02 | MEDIO | `test_compute_endpoints.py` y `test_compute_service.py` referenciados en el encargo no existen — existen como `test_compute.py` y los de consenso en `test_consensus.py` |
| R2-M-03 | MEDIO | `finalize_job` no marca el job como `validating` durante la reducción |
| R2-M-04 | MEDIO | `get_job_result` devuelve 400 cuando el job no está `completed` — semánticamente debería ser 409 o 202 |
| R2-M-05 | MEDIO | `JobResultPage.tsx`: extracción del resultado asume estructura `{operation, columns:{...}}` que no coincide con el formato real de `finalize_job` |
| R2-M-06 | MEDIO | `split_csv` vulnerable a CSV con muchas columnas vacías (ReDoS no aplica, pero sí DoS por memoria) |
| R2-B-01 | BAJO | `parseCsvText` en `NewJobPage.tsx` no maneja campos CSV con comas internas ni comillas dobles correctamente |
| R2-B-02 | BAJO | El worker cierra sesión (`sys.exit`) en caso de fallo de login, sin posibilidad de recuperación |
| R2-B-03 | BAJO | `JobDetailPage` y `JobListPage` duplican la definición de `jobStatusConfig`/`statusConfig` y `isInFlight` |
| R2-B-04 | BAJO | `JobResultPage.tsx` calcula `rewardTotal` como `total_chunks * 0.1` hardcodeado, ignorando el `reward_total` que ya viene del backend |
| R2-B-05 | BAJO | Acento tipográfico faltante en banner de `JobDetailPage.tsx` ("exito" → "éxito") |
| R2-INFO-01 | INFO | `get_valid_results_for_job` y `count_done_and_rejected_chunks` abren conexiones psycopg2 sin pool — mismo patrón señalado en A-06 de la revisión anterior |
| R2-INFO-02 | INFO | La migración `004_compute.sql` es idempotente y bien documentada |
| R2-INFO-03 | INFO | El sistema de plugins (`WorkerPlugin` + `get_plugin`) está correctamente diseñado para extensibilidad futura |

---

### CRÍTICOS

#### R2-C-01 — `JobListPage.tsx` no compila: `Link` y `Button` usados sin importar

**Archivo:** `frontend/src/pages/JobListPage.tsx`, líneas 87, 124, 185, 192

**Descripción:**
El componente `JobCard` usa `<Link to={...}>` (react-router-dom) en las líneas 87 y 124, y el componente `JobListPage` usa `<Button>` en las líneas 185 y 192. Ninguno de los dos está en los imports del fichero. Los imports presentes son:

```
import { useNavigate, useLocation } from 'react-router-dom'  // solo navigate y location, no Link
// No hay import de Button
```

TypeScript/`tsc` rechazará este fichero con error `Cannot find name 'Link'` y `Cannot find name 'Button'`, haciendo que el build del frontend falle completamente. La página `JobListPage` queda inaccesible en producción.

**Impacto:** Build del frontend roto. La ruta `/jobs` no puede compilarse ni renderizarse.

**Corrección:**
```typescript
// Añadir a los imports existentes de react-router-dom:
import { useNavigate, useLocation, Link } from 'react-router-dom'

// Añadir import de Button (junto a los imports de componentes UI):
import Button from '../components/ui/Button'
```

---

#### R2-C-02 — `credit_reward` reutiliza `update_wallet_on_task_complete` no-atómico

**Archivo:** `backend/app/services/wallet_service.py`, líneas 106–125
**Archivo relacionado:** `backend/app/db/queries/wallet_queries.py`, líneas 84–110

**Descripción:**
La nueva función `credit_reward` llama a `wallet_queries.update_wallet_on_task_complete`, que ya fue marcada como CRÍTICO (C-03) en la revisión anterior por su patrón leer-modificar-escribir sin atomicidad. El nuevo código de la feature de cómputo real hereda ese bug directamente: cuando dos chunks de un mismo proveedor se validan concurrentemente, ambas llamadas a `credit_reward` pueden leer el mismo saldo base y ambas escribir sobre él, perdiendo una de las recompensas.

Este riesgo es especialmente real en el contexto de esta feature: un proveedor con `replicas_needed=2` puede tener dos chunks validados casi simultáneamente (cuando dos workers entregan su segundo resultado casi al mismo tiempo). En ese escenario, ambos flujos de `process_chunk_submission` llaman a `_pay_and_update_trust`, que llama a `credit_reward`, que hace la lectura-modificación-escritura no protegida.

**Impacto:** Pérdida de recompensas para los proveedores. Inconsistencia en `available_balance` y `total_earned`. El proveedor recibe menos CC de lo que le corresponde.

**Corrección:** Aplicar el fix ya recomendado en C-03 de la revisión anterior. En `wallet_queries.update_wallet_on_task_complete`, reemplazar el doble round-trip por:
```sql
UPDATE wallets
SET available_balance = available_balance + %s,
    total_earned      = total_earned + %s,
    updated_at        = now()
WHERE provider_id = %s
RETURNING *
```
Esto es atómico a nivel de motor PostgreSQL y elimina la ventana de concurrencia.

---

#### R2-C-03 — `_pay_and_update_trust` no es transaccional: pago y trust en pasos separados

**Archivo:** `backend/app/services/consensus_service.py`, líneas 43–85

**Descripción:**
La función `_pay_and_update_trust` ejecuta en secuencia:
1. `wallet_service.credit_reward(...)` — acredita CC al proveedor.
2. `get_provider_by_id(...)` — lee el proveedor.
3. Calcula nuevo `accuracy` y `trust_score`.
4. `update_provider(...)` — actualiza accuracy, trust_score y rank.

Si el paso 4 falla (error de red, timeout, error en la BD) después de que el paso 1 haya tenido éxito, el proveedor recibe el pago pero su trust score nunca se actualiza. El bloque `except` general en la línea 78 captura la excepción y solo registra un log de error (`logger.error`), sin ningún mecanismo de compensación ni reintento. El proveedor queda con saldo correcto pero trust score desactualizado.

La misma inconsistencia aplica en el camino inverso: si el pago fallase pero la lectura del proveedor y el cálculo de trust ya ocurrieron, el trust se actualizaría correctamente pero el dinero no llegaría.

**Impacto:** Inconsistencia entre estado financiero y estado de reputación del proveedor. Dificulta auditorías y reconciliación. No hay mecanismo de recuperación.

**Corrección:** En el corto plazo, reestructurar `_pay_and_update_trust` para que no silencia el error — si el pago tuvo éxito y el trust falla, debe quedar en un log que permita reconciliación manual, y la excepción debe propagarse para que el caller (`process_chunk_submission`) pueda devolver un 500 en vez de una respuesta exitosa falsa. En el medio plazo, mover ambas operaciones a una única transacción de BD o usar un patrón outbox para garantizar exactly-once semantics.

---

### ALTOS

#### R2-A-01 — `HTTP_413_REQUEST_ENTITY_TOO_LARGE` deprecado (QA bug #1 — NO corregido)

**Archivo:** `backend/app/routers/compute.py`, línea 79

**Descripción:**
El QA identificó este problema. En Starlette/FastAPI moderno, la constante correcta es `HTTP_413_CONTENT_TOO_LARGE`. La constante `HTTP_413_REQUEST_ENTITY_TOO_LARGE` fue deprecada y puede producir un `AttributeError` en versiones futuras de Starlette.

**Código actual:**
```python
status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
```

**Corrección:**
```python
status_code=status.HTTP_413_CONTENT_TOO_LARGE,
```

---

#### R2-A-02 — `class Config` en `JobPublic` (QA bug #2 — NO corregido)

**Archivo:** `backend/app/models/compute.py`, líneas 32–33

**Descripción:**
El QA identificó este problema. `class Config` es la sintaxis de Pydantic v1 y está deprecada en Pydantic v2. El resto del proyecto ya usa Pydantic v2 y este modelo debería ser consistente.

**Código actual:**
```python
class Config:
    from_attributes = True
```

**Corrección:**
```python
from pydantic import BaseModel, ConfigDict, Field
...
class JobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ...
```

---

#### R2-A-03 — Submit duplicado devuelve 400 en vez de 409 (QA bug #3 — NO corregido)

**Archivo:** `backend/app/services/consensus_service.py`, líneas 156–160

**Descripción:**
El QA identificó este problema (US-36 CA-2). Cuando un proveedor intenta entregar un resultado para un chunk para el que ya ha entregado resultado, el sistema devuelve `HTTP_400_BAD_REQUEST`. El backlog pide explícitamente `409 Conflict` para este caso.

**Código actual:**
```python
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Ya has entregado un resultado para este chunk",
)
```

**Corrección:**
```python
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Ya has entregado un resultado para este chunk",
)
```

**Impacto secundario:** El test `test_k07_duplicate_submit_returns_400` (test_consensus.py línea 361) espera `status_code == 400` y necesita actualizarse a `409` al hacer este cambio.

---

#### R2-A-04 — US-38 CA-8: chunk con >5 intentos no se marca como `rejected` (QA bug #4 — NO implementado)

**Archivo:** `backend/app/db/queries/compute_queries.py`, función `claim_chunks_atomic`, líneas 165–230
**Archivo relacionado:** `backend/app/services/consensus_service.py`

**Descripción:**
El brief (US-38 CA-8) y el QA identifican que un chunk con más de 5 intentos fallidos (`attempts > 5`) debe marcarse automáticamente como `rejected` para evitar que quede atascado en un bucle indefinido de reasignaciones. Esta lógica no existe en ningún lugar del código.

`claim_chunks_atomic` incrementa `attempts` en cada reclamación, pero nunca verifica si el límite fue superado. Un chunk que nunca llega a consenso puede acumular intentos indefinidamente, consumiendo recursos de workers y bloqueando potencialmente la finalización del job padre.

**Corrección:** Añadir en `claim_chunks_atomic` una segunda actualización que marque como `rejected` los chunks que superen el umbral, o añadir una llamada en `process_chunk_submission` después de insertar el resultado: si `chunk["attempts"] > 5` y el chunk sigue sin validarse, marcarlo `rejected` y llamar a `_try_close_job`. Ejemplo de SQL a añadir al final del CTE en `claim_chunks_atomic`:

```sql
-- Tras el UPDATE principal, rechazar chunks con demasiados intentos:
UPDATE chunks SET status = 'rejected'
WHERE job_id IN (SELECT DISTINCT job_id FROM candidates)
  AND status = 'assigned'
  AND attempts > 5
```

O bien añadir la verificación en `process_chunk_submission` antes de devolver la respuesta.

---

#### R2-A-05 — `create_job_with_chunks` no es atómica: job se persiste aunque fallen los chunks

**Archivo:** `backend/app/services/compute_service.py`, líneas 163–186

**Descripción:**
La secuencia de creación en `create_job_with_chunks` es:
1. `compute_queries.create_job(...)` — inserta la fila en `jobs` con `status=pending`.
2. `compute_queries.update_job_status(job_id, "splitting")` — actualiza a `splitting`.
3. `compute_queries.create_chunks(...)` — inserta N filas en `chunks`.
4. `compute_queries.update_job_chunks_count(...)` — actualiza `total_chunks`.

Si el paso 3 falla (p.ej. error de BD, payload demasiado grande para jsonb), el job queda en estado `splitting` en la BD sin chunks asociados. No existe ningún mecanismo de rollback: el job permanece "atascado" en `splitting` indefinidamente, aparece en el dashboard del cliente como activo, y nunca puede completarse.

El bloque `except Exception` en las líneas 179–186 captura el error y lanza un 500 al cliente, pero la fila del job ya está persistida en la BD.

**Impacto:** Jobs fantasma en estado `splitting` que nunca progresan ni pueden eliminarse (no hay endpoint DELETE /jobs). Si el cliente reintenta la operación, crea un nuevo job, dejando el anterior corrupto.

**Corrección:** Envolver los pasos 1–4 en una transacción psycopg2 explícita, o añadir lógica de compensación que marque el job como `failed` en el bloque `except`:
```python
except Exception as exc:
    logger.error("Error creando job: %s", exc, exc_info=True)
    # Compensación: marcar el job como failed si ya fue creado
    if 'job_id' in locals():
        try:
            compute_queries.update_job_status(job_id, "failed")
        except Exception:
            pass
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error interno del servidor",
    )
```

---

#### R2-A-06 — `claim_chunks_atomic` sobrescribe `assigned_to` con un único proveedor por chunk

**Archivo:** `backend/app/db/queries/compute_queries.py`, líneas 165–230
**Archivo relacionado:** `migrations/004_compute.sql`, línea 97

**Descripción:**
El esquema de la tabla `chunks` tiene `assigned_to uuid` — un único UUID. El brief especifica `replicas_needed=2`, lo que significa que dos proveedores distintos deben procesar el mismo chunk.

Cuando el primer proveedor reclama el chunk, `claim_chunks_atomic` hace `SET assigned_to = provider_id_1` y `SET status = 'assigned'`. Cuando el segundo proveedor reclama el mismo chunk (ya en `status=assigned`... pero el query WHERE filtra `status='pending'`), el chunk NO puede ser reclamado por el segundo proveedor porque su status ya no es `pending`. El único mecanismo actual para que el segundo proveedor acceda al chunk es que el primero entregue su resultado y el chunk sea válido — pero si el primer proveedor entrega un resultado y hay `replicas_needed=2`, el chunk queda en `assigned` esperando la segunda réplica sin que ningún worker pueda reclamarlo.

La query SQL de `claim_chunks_atomic` sólo selecciona `WHERE c.status = 'pending'`. Un chunk con `status='assigned'` (asignado al primer proveedor, esperando segunda réplica) es invisible para todos los demás workers. El segundo worker nunca puede reclamar ese chunk.

**Impacto:** El consenso de 2 réplicas nunca puede completarse. Todos los jobs quedan atascados esperando réplicas que nadie puede reclamar. La feature central del brief no funciona correctamente end-to-end.

**Corrección:** Cambiar la condición de elegibilidad en `claim_chunks_atomic` para incluir chunks en estado `pending` O chunks en `assigned` que tengan menos resultados entregados que `replicas_needed`:
```sql
WHERE (
    c.status = 'pending'
    OR (
        c.status = 'assigned'
        AND (
            SELECT COUNT(*) FROM chunk_results cr2
            WHERE cr2.chunk_id = c.id
        ) < c.replicas_needed
    )
)
AND NOT EXISTS (
    SELECT 1 FROM chunk_results cr
    WHERE cr.chunk_id = c.id
      AND cr.provider_id = %(provider_id)s
)
```
Y al hacer el UPDATE, no pisar `assigned_to` si el chunk ya tenía un asignado — o usar una columna `assigned_to_list` (array de UUIDs) si se quiere tracking detallado.

---

### MEDIOS

#### R2-M-01 — `REWARD_PER_CHUNK` definido en tres módulos distintos

**Archivos:**
- `backend/app/db/queries/compute_queries.py`, línea 22: `REWARD_PER_CHUNK = 0.10`
- `backend/app/services/compute_service.py`, línea 25: `REWARD_PER_CHUNK = 0.10`
- `backend/app/services/consensus_service.py`, línea 30: `REWARD_PER_CHUNK = 0.10`

**Descripción:** La constante de recompensa está triplicada. Si el valor cambia en el futuro (decisión de negocio), hay que actualizar tres sitios, con riesgo de inconsistencia.

**Corrección:** Centralizar en `backend/app/core/config.py` o en un módulo `backend/app/core/constants.py` e importar desde allí.

---

#### R2-M-02 — Los ficheros de test nombrados en el encargo no existen con esos nombres

**Descrito en el encargo:** `test_compute_endpoints.py` y `test_compute_service.py`
**Existente en el repositorio:** `test_compute.py` y `test_consensus.py`

**Descripción:** El encargo de revisión solicita revisar `test_compute_endpoints.py` y `test_compute_service.py`, que no existen. Los tests de endpoints de cómputo están en `test_compute.py` y los del servicio de consenso en `test_consensus.py`. No es un bug funcional, pero indica un desajuste entre la documentación del encargo y la implementación real.

**Corrección:** Renombrar los archivos de test para que coincidan con la convención descrita en los docs de arquitectura, o actualizar el encargo y los comentarios de referencia en los propios tests (que citan `§12.9` pero los nombres de test son `C-01`...`C-05` y `K-01`...`K-07`).

---

#### R2-M-03 — `finalize_job` no transiciona el job por el estado `validating`

**Archivo:** `backend/app/services/compute_service.py`, líneas 246–319
**Archivo relacionado:** `migrations/004_compute.sql`, línea 45

**Descripción:**
El schema define el estado `validating` para el job. Sin embargo, `finalize_job` pasa directamente de `processing` a `completed` sin pasar por `validating`. El estado `validating` nunca es asignado a ningún job en el código actual. Los clientes que están haciendo polling de `GET /jobs/{id}` nunca verán el estado `validating` en la UI, haciendo que el badge y la lógica de polling para ese estado sean código muerto.

**Corrección:** Al inicio de `finalize_job`, marcar el job como `validating` mientras se realiza la reducción de resultados, y después marcar como `completed`. Alternativamente, documentar que el estado `validating` está reservado para una implementación futura y ajustar el badge de la UI.

---

#### R2-M-04 — `get_job_result` devuelve `HTTP_400_BAD_REQUEST` cuando el job no está completado

**Archivo:** `backend/app/services/compute_service.py`, líneas 231–234

**Descripción:**
Cuando se llama a `GET /jobs/{id}/result` y el job está en estado `processing`, el endpoint devuelve 400. Semánticamente, 400 indica "petición malformada del cliente". En este caso la petición es correctamente formada — simplemente el recurso no está disponible aún. El código HTTP más apropiado sería 409 Conflict (el estado actual del recurso impide satisfacer la petición) o 202 Accepted (el procesamiento está en curso).

**Corrección:**
```python
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail=f"El job aún no ha sido completado (estado actual: {job_public.status})",
)
```

---

#### R2-M-05 — `JobResultPage.tsx` asume una estructura del resultado que no coincide con `finalize_job`

**Archivo:** `frontend/src/pages/JobResultPage.tsx`, líneas 114–122

**Descripción:**
La página extrae datos del resultado así:
```typescript
const resultData = result.result as Record<string, unknown>
const operation = typeof resultData.operation === 'string' ? resultData.operation : '—'
const columnsResult = (
  typeof resultData.columns === 'object' && resultData.columns !== null
    ? resultData.columns
    : {}
) as Record<string, unknown>
const tableRows = Object.entries(columnsResult)
```
Asume que `result.result` tiene la forma `{ operation: "mean", columns: { col1: 1.5, col2: 3.0 } }`.

Sin embargo, `finalize_job` en `compute_service.py` genera el resultado con la estructura plana:
`{ "col1_mean": 1.5, "col2_mean": 3.0 }` (claves con sufijo `_<operation>`).

Resultado: `tableRows` siempre estará vacío (la llave `columns` no existe en el objeto real), y la tabla de resultados mostrará el mensaje "No hay datos de columnas disponibles" para todos los jobs completados.

**Impacto:** La página de resultados es funcionalmente inútil — nunca muestra los valores calculados.

**Corrección:** Cambiar la extracción para usar directamente las claves del objeto `result.result`:
```typescript
const resultData = result.result as Record<string, unknown>
const tableRows = Object.entries(resultData).filter(
  ([key]) => !key.startsWith('__')  // excluir claves internas del reductor
)
```
Y derivar `operation` de los parámetros del job (o de la URL, o del sufijo de las claves del resultado).

---

#### R2-M-06 — `split_csv` no limita el número de columnas ni el tamaño de la fila

**Archivo:** `backend/app/services/compute_service.py`, líneas 48–83

**Descripción:**
`split_csv` no valida el número de columnas del CSV ni el tamaño de las filas. Un CSV válido con miles de columnas puede crear payloads jsonb extremadamente grandes en `chunks.payload`, superando potencialmente los límites de Supabase/PostgreSQL o causando problemas de memoria durante la serialización.

**Corrección:** Añadir una validación razonable:
```python
MAX_COLUMNS = 200
if len(headers) > MAX_COLUMNS:
    raise ValueError(f"El CSV no puede tener más de {MAX_COLUMNS} columnas")
```

---

### BAJOS

#### R2-B-01 — `parseCsvText` en `NewJobPage.tsx` no maneja CSV con comas internas correctamente

**Archivo:** `frontend/src/pages/NewJobPage.tsx`, líneas 45–53

**Descripción:**
El parser CSV del frontend usa un split naivo por comas: `line.split(',')`. Un campo con comas internas dentro de comillas dobles (ej. `"valor, con coma"`) se partirá incorrectamente. Esto crea una discrepancia entre la vista previa del frontend (columnas y recuento de filas) y lo que realmente procesa el backend con `csv.reader` (que sí maneja el estándar RFC 4180 completo).

**Corrección:** Usar la API `FileReader` junto con una librería CSV válida para el frontend (ej. `papaparse`), o al menos avisar al usuario que los campos con comas internas pueden no mostrarse correctamente en la vista previa.

---

#### R2-B-02 — El worker llama `sys.exit(1)` en fallo de login sin posibilidad de recuperación

**Archivo:** `backend/app/worker/main.py`, líneas 41–48

**Descripción:**
Si el servidor devuelve un error transitorio (503, timeout, error de red) durante el login inicial, el worker termina con `sys.exit(1)` sin ningún reintento. Para un proceso diseñado para ser resiliente y lanzarse con scripts de múltiples workers, un fallo de login transitorio debería retentarse con backoff.

**Corrección:** Reemplazar `sys.exit(1)` en el login por un mecanismo de reintento con número máximo de intentos configurables, o por lo menos con un reintento inicial antes de terminar.

---

#### R2-B-03 — `statusConfig` y `isInFlight` están duplicados entre `JobDetailPage` y `JobListPage`

**Archivos:**
- `frontend/src/pages/JobDetailPage.tsx`, líneas 21–49 y 73–79
- `frontend/src/pages/JobListPage.tsx`, líneas 21–52 y 77–80

**Descripción:** La configuración de badges de estado de job y la función `isInFlight` son casi idénticas en ambas páginas. La única diferencia es que `JobDetailPage` usa etiquetas más largas ("Dividiendo en chunks", "Validando resultados").

**Corrección:** Extraer un hook o módulo `useJobStatus.ts` con la configuración de estados y la función `isInFlight` y reutilizarlo en ambas páginas.

---

#### R2-B-04 — `JobResultPage.tsx` recalcula `rewardTotal` en el cliente en vez de usar el dato del backend

**Archivo:** `frontend/src/pages/JobResultPage.tsx`, línea 129

**Descripción:**
```typescript
const rewardTotal = result.total_chunks * 0.1
```
El valor `0.1` está hardcodeado. El backend ya calcula y almacena `reward_total` en la tabla `jobs`. El endpoint `GET /jobs/{id}/result` devuelve `JobResultResponse`, que no incluye `reward_total`. Si la recompensa por chunk cambia en el futuro, este cálculo del frontend quedará desincronizado.

**Corrección:** Añadir `reward_total` a `JobResultResponse` en el backend (tanto en el modelo Pydantic como en la función `get_job_result` de `compute_service.py`), actualizar el tipo `JobResultResponse` en `frontend/src/types/compute.ts`, y usar ese valor en la página.

---

#### R2-B-05 — Errores tipográficos menores en las nuevas páginas

**Archivos:**
- `frontend/src/pages/JobDetailPage.tsx`, línea 193: `"Trabajo completado con exito"` → falta tilde → `"Trabajo completado con éxito"`
- `frontend/src/pages/JobDetailPage.tsx`, línea 265: `"Operacion"` → `"Operación"`
- `frontend/src/pages/JobResultPage.tsx`, línea 162: `"Operacion:"` → `"Operación:"`
- `frontend/src/pages/JobResultPage.tsx`, línea 224: `"Operacion"` → `"Operación"`
- `frontend/src/pages/JobResultPage.tsx`, línea 243: `"Duracion total"` → `"Duración total"`

**Impacto:** Baja, pero visible en producción para usuarios en español.

---

### INFO

#### R2-INFO-01 — Conexiones psycopg2 sin pool en `compute_queries.py`

**Archivo:** `backend/app/db/queries/compute_queries.py`, líneas 129, 202, 343, 363

Cuatro funciones abren conexiones psycopg2 directas sin pooling: `increment_job_completed_chunks`, `claim_chunks_atomic`, `get_valid_results_for_job`, `count_done_and_rejected_chunks`. Este es el mismo patrón señalado en A-06 de la revisión anterior. Las operaciones atómicas (claim, increment) justifican el uso de psycopg2, pero las de sólo lectura (`get_valid_results_for_job`, `count_done_and_rejected_chunks`) podrían evitar psycopg2 usando el SDK de Supabase con joins.

---

#### R2-INFO-02 — Migración `004_compute.sql` bien diseñada

La migración es idempotente (`IF NOT EXISTS`, `DROP POLICY IF EXISTS`), bien comentada, incluye todas las constraints definidas en el brief, los índices necesarios y documenta explícitamente por qué las políticas de usuario con `auth.uid()` no tienen efecto en el contexto actual. No hay hallazgos de mejora.

---

#### R2-INFO-03 — Sistema de plugins correctamente extensible

La arquitectura `WorkerPlugin` → `DataProcessingPlugin` → registro en `__init__.py` está limpiamente diseñada. Añadir `TranscriptionPlugin` o `RenderPlugin` en el futuro requiere solo crear el módulo y registrar la clase — sin tocar el núcleo del worker. El `SECURITY NOTE` en el docstring de `worker/main.py` documenta correctamente el riesgo de sandbox.

---

### Resumen ejecutivo de esta revisión

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| CRÍTICO   | 3        | R2-C-01, R2-C-02, R2-C-03 |
| ALTO      | 6        | R2-A-01 a R2-A-06 |
| MEDIO     | 6        | R2-M-01 a R2-M-06 |
| BAJO      | 5        | R2-B-01 a R2-B-05 |
| INFO      | 3        | R2-INFO-01 a R2-INFO-03 |
| **Total** | **23**   | |

### Estado de los bugs identificados por QA

| Bug QA | Estado | Hallazgo |
|--------|--------|----------|
| #1 — HTTP_413_REQUEST_ENTITY_TOO_LARGE deprecado | **NO corregido** | R2-A-01 |
| #2 — class Config en modelos Pydantic | **NO corregido** | R2-A-02 |
| #3 — Submit duplicado devuelve 400 en vez de 409 | **NO corregido** | R2-A-03 |
| #4 — Chunk >5 intentos no se marca como rejected | **NO implementado** | R2-A-04 |

Los 4 bugs identificados por QA siguen sin estar resueltos en el código revisado.

### Veredicto

**RECHAZADO**

La feature no puede mergearse en su estado actual por los siguientes motivos:

1. **R2-C-01** — El frontend no compila. `JobListPage.tsx` tiene referencias a `Link` y `Button` no importados. El build falla antes de llegar a producción.

2. **R2-A-06** — La lógica de réplicas está rota. El mecanismo de consenso con `replicas_needed=2` no puede completarse porque el segundo proveedor nunca puede reclamar un chunk ya en estado `assigned`. La funcionalidad central del brief (consenso distribuido) no es operable.

3. **R2-M-05** — `JobResultPage` siempre muestra "No hay datos disponibles" porque asume una estructura de resultado que no coincide con la que genera el backend.

4. **Los 4 bugs del QA** siguen sin estar corregidos.

### Blockers antes de mergear

Los siguientes hallazgos deben resolverse antes del merge:

1. **R2-C-01** — Añadir imports de `Link` y `Button` en `JobListPage.tsx`.
2. **R2-A-01** — Cambiar `HTTP_413_REQUEST_ENTITY_TOO_LARGE` → `HTTP_413_CONTENT_TOO_LARGE`.
3. **R2-A-02** — Migrar `class Config` → `model_config = ConfigDict(from_attributes=True)`.
4. **R2-A-03** — Cambiar respuesta de submit duplicado de 400 → 409 (y actualizar test K-07).
5. **R2-A-04** — Implementar rechazo de chunks con >5 intentos.
6. **R2-A-05** — Añadir compensación de estado `failed` cuando la creación de chunks falla.
7. **R2-A-06** — Corregir `claim_chunks_atomic` para permitir reclamar chunks con réplicas pendientes.
8. **R2-M-05** — Corregir `JobResultPage.tsx` para extraer resultados de la estructura real generada por `finalize_job`.
9. **R2-C-02 / R2-C-03** — Aplicar el fix atómico en `update_wallet_on_task_complete` y añadir manejo de fallos parciales en `_pay_and_update_trust`.

---

### Handoff al Security Auditor — Feature Cómputo Real

Los puntos de seguridad específicos de esta feature que el Security Auditor debe evaluar:

1. **Payload no sanitizado en chunks**: Los datos que los clientes suben (CSV o `params["data"]`) se almacenan directamente en `chunks.payload` (jsonb) y son devueltos a los workers sin ningún filtrado. Un cliente malicioso podría incluir datos diseñados para explotar bugs en el plugin del worker. El brief menciona explícitamente que el sandboxing del worker está fuera de alcance, pero el auditor debe documentar el vector de ataque y su criticidad.

2. **Worker autentica con credenciales en línea de comandos**: El comando `python -m app.worker --email X --password Y` expone credenciales en el historial de shell y en `ps aux`. Verificar que los workers de producción no usen este mecanismo directamente — se necesita inyección por variable de entorno o secret manager.

3. **Sin rate limiting en `POST /work/claim`**: Un atacante autenticado como proveedor puede llamar a `POST /work/claim` con `max_chunks=10` de forma intensiva, reclamando todos los chunks disponibles sin procesarlos realmente, bloqueando a otros workers legítimos. No hay timeout de asignación (los chunks `assigned` nunca se devuelven automáticamente a `pending`).

4. **Sin timeout de asignación de chunks**: Si un worker reclama chunks y luego desaparece (crash, disconnect), esos chunks quedan en estado `assigned` indefinidamente. No hay ningún job scheduler ni TTL que los devuelva a `pending`. Esto también impide que el job llegue a completarse.

5. **`GET /jobs/{id}/result` leakea información de estado**: El endpoint devuelve el estado actual del job en el mensaje de error aunque el job no sea del cliente autenticado — la verificación de ownership se hace correctamente en `get_job_status`, pero vale la pena confirmar que el 403 no filtra información del job ajeno en el `detail`.

6. **Consenso gamificable**: Un proveedor puede registrarse con múltiples cuentas y procesar el mismo chunk dos veces como "réplicas distintas", obteniendo doble recompensa y garantizando consenso artificialmente. La única protección actual es la constraint `UNIQUE (chunk_id, provider_id)` en `chunk_results`, que previene el doble submit con la misma cuenta pero no con cuentas Sybil.
