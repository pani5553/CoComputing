# Co-Computing

Plataforma web de computación distribuida descentralizada. Permite a proveedores de cómputo ofrecer la capacidad de sus máquinas, aceptar tareas de procesamiento, monitorizar el progreso en tiempo real y cobrar recompensas en CC (Co-Computing Coin).

**Para quién es:** proveedores de cómputo (personas u organizaciones con hardware disponible que quieren monetizar su capacidad de procesamiento).

**Stack:**
- Frontend: React 18 + Vite + TypeScript + Zustand + Tailwind CSS
- Backend: FastAPI (Python 3.12) + Uvicorn
- Base de datos / Auth: Supabase (PostgreSQL 15), JWT HS256, 7 dias de expiracion

---

## Requisitos previos

| Herramienta | Version minima | Necesario para |
|-------------|---------------|----------------|
| Docker + Docker Compose | 24+ | Arranque rapido (recomendado) |
| Python | 3.12+ | Arranque local sin Docker |
| Node.js | 20+ | Arranque local sin Docker |
| Cuenta Supabase | — | Siempre (base de datos en la nube) |

---

## Arranque rapido con Docker (opcion recomendada)

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio> co-computing
cd co-computing
```

### 2. Crear el archivo de entorno

```bash
cp deploy/env.example backend/.env
```

Editar `backend/.env` con los valores reales de tu proyecto Supabase (ver seccion [Variables de entorno](#variables-de-entorno)).

### 3. Aplicar el schema en Supabase

Antes de arrancar los contenedores, ejecuta las migraciones en el SQL Editor de tu proyecto Supabase, en este orden:

1. `migrations/001_schema.sql` — crea las 5 tablas, triggers e indices
2. `migrations/002_rls.sql` — activa Row Level Security

> **No ejecutes `migrations/003_seed.sql` en produccion.** Contiene una cuenta demo con credenciales publicas en GitHub. Solo para entornos de desarrollo/demo.

### 4. Arrancar los contenedores

```bash
bash deploy/start-local.sh
```

O directamente con Docker Compose:

```bash
docker compose build --pull
docker compose up -d
```

Los Dockerfiles estan en `deploy/`. El build context es la raiz del repositorio.

### 5. Verificar que esta en marcha

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API docs (solo desarrollo) | http://localhost:8000/docs |

Ver logs en tiempo real:

```bash
docker compose logs -f
```

Detener:

```bash
docker compose down
```

---

## Arranque local sin Docker (para desarrollo)

### Backend

```bash
cd backend

# Crear y activar entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Supabase y JWT_SECRET_KEY

# Arrancar el servidor
uvicorn app.main:app --reload --port 8000
```

Backend disponible en `http://localhost:8000`. Documentacion interactiva en `http://localhost:8000/docs` (solo en modo development).

### Frontend

```bash
cd frontend

npm install

# Configurar la URL del backend (opcional, por defecto apunta a localhost:8000)
cp .env.example .env

npm run dev
```

Frontend disponible en `http://localhost:5173`.

---

## Configuracion de Supabase

1. Crear un proyecto en [supabase.com](https://supabase.com).
2. En el panel, ir a **Settings → API** y copiar:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (nunca la clave `anon`)
3. En **Settings → Database → Connection string**, copiar la cadena del **Transaction Pooler** (puerto 6543) → `SUPABASE_DB_URL`.
4. Ejecutar las migraciones en el **SQL Editor** de Supabase en este orden:
   - `migrations/001_schema.sql`
   - `migrations/002_rls.sql`
5. Generar `JWT_SECRET_KEY` con:

```bash
openssl rand -hex 32
```

> **Advertencia:** `migrations/003_seed.sql` inserta la cuenta `demo@co-computing.io` con la contrasena `demo1234` y un hash publico en GitHub. **Nunca ejecutar en produccion.** Solo para demostraciones en local.

---

## Variables de entorno

Todas las variables del backend van en `backend/.env`. Para el arranque con Docker puedes partir de `deploy/env.example`.

### Backend (`backend/.env`)

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `SUPABASE_URL` | URL del proyecto Supabase | `https://xxxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave service_role (bypasea RLS). Nunca exponer al cliente | `eyJ...` |
| `SUPABASE_DB_URL` | Cadena de conexion psycopg2, puerto 6543 (transaction pooler) | `postgresql://postgres.ref:pwd@host:6543/postgres` |
| `JWT_SECRET_KEY` | Secreto JWT, minimo 32 caracteres. Generar con `openssl rand -hex 32` | `a3f8b2c9...` |
| `JWT_ALGORITHM` | Algoritmo de firma JWT | `HS256` |
| `JWT_EXPIRE_DAYS` | Dias de validez del token de sesion | `7` |
| `FRONTEND_URL` | URL exacta del frontend para CORS, sin trailing slash | `http://localhost:3000` |
| `ENVIRONMENT` | `development` activa `/docs` y `/redoc`. `production` los desactiva | `development` |

### Frontend (`frontend/.env`)

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `VITE_API_URL` | URL base del backend sin trailing slash | `http://localhost:8000` |

> **Importante:** `VITE_API_URL` es una variable de tiempo de build en Vite. Si cambias la URL del backend en produccion, debes reconstruir la imagen del frontend (`docker compose build frontend`).

---

## Seed de datos de demo

El archivo `migrations/003_seed.sql` inserta 18 tareas de ejemplo y una cuenta de proveedor demo.

Solo ejecutar en entornos de desarrollo o demostracion, **nunca en produccion**:

```sql
-- Ejecutar en el SQL Editor de Supabase (solo en desarrollo/demo)
-- migrations/003_seed.sql
```

Credenciales de la cuenta demo (solo para local):
- Email: `demo@co-computing.io`
- Contrasena: `demo1234`

El hash de esta contrasena esta publicado en el repositorio. La cuenta no debe existir en produccion bajo ningun concepto.

---

## Endpoints de la API

La documentacion interactiva completa esta disponible en `http://localhost:8000/docs` (solo en modo development).

| Metodo | Ruta | Autenticacion | Descripcion |
|--------|------|---------------|-------------|
| POST | `/auth/register` | No | Registro de proveedor |
| POST | `/auth/login` | No | Login, devuelve JWT (7 dias) |
| GET | `/auth/me` | Si | Perfil del proveedor autenticado |
| GET | `/tasks/` | Si | Listado de tareas con filtros |
| GET | `/tasks/my/history` | Si | Historial de asignaciones del proveedor |
| GET | `/tasks/{task_id}` | Si | Detalle de tarea |
| POST | `/tasks/{task_id}/accept` | Si | Acepta tarea (decremento atomico de plazas) |
| POST | `/tasks/{task_id}/start` | Si | Inicia procesamiento |
| POST | `/tasks/{task_id}/complete` | Si | Completa tarea y acredita recompensa |
| POST | `/tasks/{task_id}/fail` | Si | Reporta fallo |
| GET | `/tasks/assignments/{id}/progress` | Si | Progreso simulado (polling cada 3 s) |
| GET | `/wallet/` | Si | Saldos de cartera |
| GET | `/wallet/transactions` | Si | Historial de transacciones paginado |
| POST | `/wallet/withdraw` | Si | Solicitar retiro de fondos |
| GET | `/profile/stats` | Si | Perfil + Trust Score + info de rango |
| PUT | `/profile/hardware` | Si | Actualizar especificaciones de hardware |
| PATCH | `/profile/online` | Si | Alternar estado online |
| PATCH | `/profile/name` | Si | Actualizar nombre completo |
| GET | `/health` | No | Health check |

---

## Tests

### Backend (pytest)

```bash
cd backend

# Activar el entorno virtual si no esta activo
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Ejecutar tests con cobertura
pytest

# Con informe HTML de cobertura
pytest --cov=app --cov-report=html
```

Cobertura minima requerida: **80%** (configurada en `pyproject.toml`). Los tests usan mocking de la base de datos; no se necesita conexion real a Supabase para ejecutarlos.

```bash
# Lint
ruff check .

# Formato
ruff format .
```

### Frontend (Vitest)

```bash
cd frontend

npm test             # ejecucion unica
npm run test:watch   # modo watch
npm run test:ui      # interfaz grafica
```

---

## Estructura del proyecto

```
co-computing/
├── backend/                    # API FastAPI
│   ├── app/
│   │   ├── main.py             # Entry point, CORS, middleware, routers
│   │   ├── core/               # Config, seguridad JWT, dependencias
│   │   ├── db/                 # Cliente Supabase, queries por dominio
│   │   ├── models/             # Esquemas Pydantic v2
│   │   ├── routers/            # auth, tasks, wallet, profile
│   │   ├── services/           # Logica de negocio (trust_score, task_lifecycle, progress)
│   │   └── seed/               # Script y SQL de seed
│   ├── tests/                  # pytest + httpx (mocking de BD)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml          # Config pytest, ruff, coverage
│   └── .env.example
├── frontend/                   # SPA React
│   ├── src/
│   │   ├── api/                # Llamadas HTTP (auth, tasks, wallet, profile)
│   │   ├── components/         # Layout, UI (Badge, Button, Card, Modal...)
│   │   ├── hooks/              # useAuth, useProgress (polling)
│   │   ├── pages/              # Login, Registro, Dashboard, Tareas, Cartera, Perfil
│   │   ├── store/              # authStore y taskStore (Zustand)
│   │   ├── types/              # Tipos TypeScript del dominio
│   │   └── utils/              # Formateo de fechas, importes y tiempos
│   ├── package.json
│   └── .env.example
├── migrations/
│   ├── 001_schema.sql          # 5 tablas, triggers, indices
│   ├── 002_rls.sql             # Row Level Security
│   └── 003_seed.sql            # Datos demo (NO ejecutar en produccion)
├── deploy/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── nginx.conf
│   ├── env.example             # Plantilla de variables para docker-compose
│   └── start-local.sh          # Script de arranque local con Docker
├── docker-compose.yml
└── .github/workflows/          # CI/CD
```

---

## Notas de produccion

### Deshabilitar la documentacion de la API

Establecer `ENVIRONMENT=production` en `backend/.env` desactiva `/docs`, `/redoc` y `/openapi.json`. El nivel de log sube a `WARNING`.

### VITE_API_URL es una variable de tiempo de build

Vite incrusta `VITE_API_URL` en el bundle durante el build. Si la URL del backend cambia en produccion, hay que reconstruir la imagen del frontend:

```bash
VITE_API_URL=https://api.tudominio.com docker compose build frontend
docker compose up -d frontend
```

### Secretos en CI/CD

Configurar los siguientes secretos en **GitHub → Settings → Secrets and variables → Actions** (nunca como variables de entorno en texto plano):

| Secreto | Descripcion |
|---------|-------------|
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave service_role |
| `SUPABASE_DB_URL` | Cadena de conexion PostgreSQL |
| `JWT_SECRET_KEY` | Secreto JWT (minimo 32 caracteres de alta entropia) |

### Migraciones

Las migraciones **no se aplican automaticamente** en Docker. Se aplican directamente contra Supabase usando la CLI de Supabase o el SQL Editor del panel web. El listado completo y actualizado de las 5 migraciones (`001_schema.sql` a `005_client.sql`) y su orden de ejecucion esta en `DEPLOY.md`, seccion "4 · Base de datos — migraciones en produccion" — se mantiene ahi como fuente unica para evitar que este README y `DEPLOY.md` diverjan.

### Checklist previo al despliegue

- [ ] `JWT_SECRET_KEY` generado con `openssl rand -hex 32`
- [ ] `ENVIRONMENT=production` configurado en el servidor
- [ ] `FRONTEND_URL` apunta al dominio de produccion (sin trailing slash, sin wildcard)
- [ ] `VITE_API_URL` apunta al dominio del backend de produccion y la imagen esta reconstruida
- [ ] `003_seed.sql` NO ejecutado en produccion
- [ ] `/docs` devuelve 404 en produccion (verificar tras el despliegue)
- [ ] Conexion SUPABASE_DB_URL usa `sslmode=require`
- [ ] `SUPABASE_SERVICE_ROLE_KEY` configurada como secret, no como variable de entorno en logs de CI

---

## Computo Real Distribuido (feature v2)

### Que es

La feature v2 anade cómputo real y verificable sobre la infraestructura existente. Un usuario sube un CSV y elige una operación (media, suma, min, max, conteo); el sistema trocea el dataset en fragmentos (chunks), varios workers Python los procesan en paralelo en sus máquinas usando polars, y los resultados se validan por consenso antes de consolidarse y pagar a los proveedores en CC. El progreso que ve el cliente es real (chunks completados / total), no simulado.

### Tablas nuevas — migración 004

Ejecutar `migrations/004_compute.sql` en el SQL Editor de Supabase, despues de las tres migraciones anteriores.

| Tabla | Proposito |
|-------|-----------|
| `jobs` | Trabajo de alto nivel enviado por el cliente. Campos clave: `status` (pending, splitting, processing, validating, completed, failed), `total_chunks`, `completed_chunks`, `reward_total`, `result` (jsonb consolidado). |
| `chunks` | Fragmento de un job. Contiene el `payload` con las filas del CSV a procesar, el `status` (pending, assigned, done, rejected) y `replicas_needed` (por defecto 2 para consenso). |
| `chunk_results` | Resultado individual que un proveedor entrega para un chunk. El campo `is_valid` (null = pendiente, true = valido, false = rechazado) lo asigna el servicio de consenso. |

### Endpoints nuevos

Todos requieren autenticacion JWT (`Authorization: Bearer <token>`).

**Lado cliente:**

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/jobs` | Crea un job. Acepta multipart/form-data (campo `file` CSV + campo `params` JSON) o JSON puro con datos embebidos. Max 10 MB. |
| `GET` | `/jobs` | Lista los jobs del cliente autenticado, ordenados por fecha descendente. |
| `GET` | `/jobs/{job_id}` | Detalle con progreso real: `progress = completed_chunks / total_chunks * 100`. |
| `GET` | `/jobs/{job_id}/result` | Resultado consolidado. Solo disponible cuando `status = completed`. Devuelve 409 si el job no ha terminado. |

**Lado worker:**

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/work/claim` | El worker reclama hasta N chunks pendientes. Asignacion atomica con `FOR UPDATE SKIP LOCKED` via psycopg2. Body: `{"max_chunks": 1}`. |
| `POST` | `/work/{chunk_id}/submit` | El worker entrega su resultado. Body: `{"result": {...}, "duration_ms": 1250}`. Dispara la logica de consenso. |

### Aplicar la migracion 004

En el SQL Editor de Supabase, ejecutar en este orden:

1. `migrations/001_schema.sql`
2. `migrations/002_rls.sql`
3. `migrations/003_seed.sql` (solo en desarrollo/demo, nunca en produccion)
4. `migrations/004_compute.sql`

El fichero `004_compute.sql` es idempotente (`CREATE TABLE IF NOT EXISTS`, `DROP POLICY IF EXISTS`).

### Lanzar un worker

El worker se autentica con las credenciales de un proveedor existente y entra en un bucle de claim-process-submit:

```bash
cd backend
python -m app.worker --api http://localhost:8000 --email tu@email.com --password tupassword
```

Parametros obligatorios:

| Parametro | Descripcion |
|-----------|-------------|
| `--api` | URL base del backend (sin trailing slash) |
| `--email` | Email del proveedor registrado en la plataforma |
| `--password` | Contrasena del proveedor |

El worker hace polling a `POST /work/claim` cada 5 segundos si no hay chunks disponibles. Se detiene con `Ctrl+C`.

### Lanzar multiples workers (demo de distribucion)

```bash
bash scripts/run_workers.sh
```

El script levanta varias instancias del worker en paralelo. Editar el script para configurar el numero de instancias y las credenciales de cada proveedor.

### Rutas nuevas del frontend

| Ruta | Descripcion |
|------|-------------|
| `/jobs` | Lista de todos los jobs del cliente con estado real y barra de progreso basada en chunks. |
| `/jobs/new` | Formulario para subir un CSV, elegir operacion y columnas, y enviar el job. |
| `/jobs/:id` | Detalle del job con progreso en tiempo real (polling cada 5 segundos mientras no este en estado terminal). |
| `/jobs/:id/result` | Resultado consolidado descargable como JSON. |

### Nota de seguridad

**El worker ejecuta computo sin sandboxing.** El proceso Python descarga payloads de la API y los procesa directamente con polars en la maquina del worker. En el MVP, el payload solo contiene datos tabulares (no codigo ejecutable) y la comunicacion es HTTPS con JWT. Sin embargo, si la API o la base de datos fuesen comprometidas, un payload malicioso podria afectar a la maquina del worker.

**Usar el worker unicamente en entornos de confianza para el MVP.** El sandboxing real (contenedor aislado con seccomp/AppArmor, verificacion HMAC del payload, ejecucion sin acceso a red) queda fuera del alcance de esta version y debe implementarse antes de usar el worker en produccion con datos de terceros no confiables.

---

## Placeholders conocidos

- **Boton "Añadir creditos" (cartera del proveedor).** En `WalletPage.tsx`, junto a "Solicitar retiro", abre un modal informativo ("Muy pronto podras comprar creditos..."). Es solo interfaz: no llama a ningun endpoint, no crea estado persistente y no tiene todavia integracion de pagos real (tarjeta, PayPal, cripto) — queda pendiente para una futura iteracion. No confundir con la recarga de saldo del lado cliente, que si es funcional (`/cliente/recargar`, `POST /wallet/deposit`).

---

## Licencia

MIT
