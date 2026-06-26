# Guía de Despliegue — Co-Computing

Esta guía cubre el despliegue del **frontend en Vercel** y el **backend en Railway**.
El despliegue real requiere tus cuentas en ambas plataformas; sigue los pasos en orden.

---

## Requisitos previos

- Repositorio en GitHub (el proyecto ya tiene `deploy/backend.Dockerfile` y `frontend/vercel.json`)
- Proyecto en Supabase activo con las migraciones aplicadas
- Variables de entorno listas (ver sección al final)

---

## 1 · Backend en Railway

### 1.1 Crear el proyecto

1. Ve a [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Selecciona tu repositorio de Co-Computing
3. Railway detectará el repositorio pero no sabrá qué Dockerfile usar; configúralo en el paso siguiente

### 1.2 Configurar el Dockerfile

En el panel de Railway del servicio:

- **Settings → Build → Dockerfile path**: `deploy/backend.Dockerfile`
- Railway construirá la imagen desde la raíz del repositorio (`context: .`)

### 1.3 Variables de entorno en Railway

En **Settings → Variables** añade todas estas (nunca las pongas en el código):

```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key del panel de Supabase>
SUPABASE_DB_URL=postgresql://postgres.<ref>:<password>@<host>:6543/postgres?sslmode=require
JWT_SECRET_KEY=<resultado de: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7
FRONTEND_URL=https://<tu-app>.vercel.app
ENVIRONMENT=production
```

> **Nota:** `FRONTEND_URL` debe coincidir exactamente con el dominio de Vercel (sin trailing slash).
> Puedes ponerla a `http://localhost:5173` temporalmente mientras configuras Vercel y actualizarla después.

### 1.4 Puerto y healthcheck

Railway expone el servicio en el puerto que el contenedor declara. El Dockerfile ya expone el **puerto 8000**. El comando de inicio es:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Para el healthcheck de Railway usa la ruta `/health`:
- **Healthcheck path:** `/health`
- **Timeout:** 10 s

### 1.5 Obtener la URL del backend

Tras el primer despliegue exitoso, Railway te dará una URL pública del tipo:
```
https://co-computing-api-<random>.up.railway.app
```

Cópiala; la necesitarás en el paso 2.3.

---

## 2 · Frontend en Vercel

### 2.1 Importar el repositorio

1. Ve a [vercel.com](https://vercel.com) → **Add New Project** → importa el mismo repositorio de GitHub
2. En la pantalla de configuración:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite (Vercel lo detecta automáticamente)
   - **Build Command:** `npm run build` *(por defecto)*
   - **Output Directory:** `dist` *(por defecto)*

### 2.2 El SPA routing funciona automáticamente

El archivo `frontend/vercel.json` ya contiene la rewrite necesaria para que React Router funcione:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Vercel lo aplica automáticamente al estar en el root directory del proyecto.

### 2.3 Variable de entorno en Vercel

En **Settings → Environment Variables** del proyecto en Vercel:

| Nombre | Valor |
|--------|-------|
| `VITE_API_URL` | `https://co-computing-api-<random>.up.railway.app` |

> Esta variable es de **build-time** (Vite la inyecta en el bundle). Después de añadirla
> debes hacer un nuevo despliegue desde **Deployments → Redeploy**.

### 2.4 Obtener la URL del frontend

Vercel te asigna una URL del tipo:
```
https://co-computing.vercel.app
```

---

## 3 · Conectar las dos URLs

Ahora que tienes ambas URLs:

1. En **Railway** → Variables → actualiza `FRONTEND_URL` al dominio de Vercel:
   ```
   FRONTEND_URL=https://co-computing.vercel.app
   ```
2. Railway redesplegará automáticamente. Verifica que el CORS funciona desde el navegador.

---

## 4 · Base de datos — migraciones en producción

Ejecuta **solo estas migraciones** en el SQL Editor de Supabase (nunca `003_seed.sql` con la cuenta demo):

```sql
-- En orden:
-- 1. migrations/001_schema.sql
-- 2. migrations/002_rls.sql
-- 3. Solo las tareas del seed (no la cuenta demo@co-computing.io)
-- 4. migrations/004_compute.sql   (si usas la feature de cómputo real)
-- 5. migrations/005_client.sql    (si usas el lado cliente)
```

> **Advertencia:** `003_seed.sql` contiene la cuenta `demo@co-computing.io / demo1234`
> con credenciales públicas en el repositorio. **No la ejecutes en producción.**

---

## 5 · Checklist final antes de publicar

- [ ] `GET https://<backend>/health` devuelve `{"status":"ok"}` (sin campo `environment`)
- [ ] `GET https://<backend>/docs` devuelve 404
- [ ] La landing (`https://<frontend>/`) carga sin errores
- [ ] El registro (`/registro`) y login (`/login`) funcionan contra el backend de prod
- [ ] El dashboard (`/dashboard`) carga correctamente tras el login
- [ ] Las llamadas API del frontend tienen `Access-Control-Allow-Origin` correcto (sin `*`)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` **no** aparece en los logs de Railway ni en el bundle de Vercel

---

## Variables de entorno — referencia completa

### Backend (Railway)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SUPABASE_URL` | URL del proyecto Supabase | `https://abc123.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave service_role (solo backend) | `eyJ...` |
| `SUPABASE_DB_URL` | Conexión directa PostgreSQL con `sslmode=require` | `postgresql://...?sslmode=require` |
| `JWT_SECRET_KEY` | Mínimo 32 chars. Generar: `openssl rand -hex 32` | `a3f9...` |
| `JWT_ALGORITHM` | Algoritmo JWT | `HS256` |
| `JWT_EXPIRE_DAYS` | Días de validez del token | `7` |
| `FRONTEND_URL` | URL exacta del frontend en Vercel | `https://co-computing.vercel.app` |
| `ENVIRONMENT` | `production` desactiva /docs y eleva log level | `production` |

### Frontend (Vercel — build-time)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `VITE_API_URL` | URL base del backend en Railway | `https://co-computing-api.up.railway.app` |

---

## Actualizar el despliegue

- **Backend:** Railway redespliega automáticamente con cada push a `main`
- **Frontend:** Vercel redespliega automáticamente con cada push a `main`

Para forzar un redespliegue sin push: en el panel de cada servicio → **Deployments → Redeploy**.
