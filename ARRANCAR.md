# 🚀 Arrancar Co-Computing en este ordenador

Guía personalizada del estado actual de **tu** equipo. Lo difícil ya está hecho;
solo te queda la parte de Supabase (5 min) porque las credenciales son tuyas.

---

## ✅ Lo que YA dejé preparado

- **Herramientas verificadas:** Python 3.14, Node 24, npm 11, Docker 29 — todo OK.
- **Frontend:** dependencias instaladas (`npm install` hecho) + `frontend/.env` creado.
- **Backend:** se ejecuta dentro de Docker con **Python 3.12** (tu Python 3.14 daba
  problemas con `psycopg2`/`pydantic`; Docker lo evita sin tocar tu sistema).
- **`backend/.env`** creado con tu `JWT_SECRET_KEY` ya generado (64 caracteres).
- **Imágenes Docker** construidas (backend + frontend).

## ⏳ Lo único que falta (lo tienes que hacer tú: son tus credenciales)

Crear una base de datos gratuita en Supabase y pegar 3 valores. **5 minutos.**

---

## Paso 1 — Crear el proyecto Supabase (gratis)

1. Entra en **https://supabase.com** → *Start your project* → inicia sesión.
2. **New project**. Ponle nombre (ej. `co-computing`), elige región (ej. *West EU*)
   y crea una **contraseña de base de datos** — **apúntala**, la necesitas en el paso 2.
3. Espera ~2 min a que el proyecto se aprovisione.

## Paso 2 — Copiar las 3 credenciales a `backend/.env`

Abre `backend/.env` y reemplaza estos 3 valores (el JWT ya está puesto, no lo toques):

| En `.env` | De dónde sacarlo en Supabase |
|-----------|------------------------------|
| `SUPABASE_URL` | **Settings → API → Project URL** (ej. `https://abcd.supabase.co`) |
| `SUPABASE_SERVICE_ROLE_KEY` | **Settings → API → Project API keys → `service_role`** (la secreta, NO la `anon`) |
| `SUPABASE_DB_URL` | **Settings → Database → Connection string → Transaction pooler** (puerto **6543**). Sustituye `[YOUR-PASSWORD]` por la contraseña del paso 1 |

## Paso 3 — Crear las tablas (migraciones)

En Supabase: **SQL Editor → New query**. Copia y ejecuta, **en este orden**:

1. Pega el contenido de **`migrations/001_schema.sql`** → *Run*.
2. Pega el contenido de **`migrations/002_rls.sql`** → *Run*.
3. *(Opcional, para tener datos de ejemplo y una cuenta de prueba)* pega
   **`migrations/003_seed.sql`** → *Run*. Esto crea 18 tareas y la cuenta demo:
   - **Email:** `demo@co-computing.io`  **Contraseña:** `demo1234`
   - ⚠️ Solo para tu local/demo. Nunca en producción.

## Paso 4 — Arrancar

Abre una terminal en esta carpeta y:

```powershell
docker compose up -d
```

Espera ~15 s (el backend tiene un health-check). Comprueba:

| Servicio | URL |
|----------|-----|
| **Frontend (la app)** | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Documentación API | http://localhost:8000/docs |

## Paso 5 — Entrar

Abre **http://localhost:3000**. Si ejecutaste el seed (paso 3.3), entra con
`demo@co-computing.io` / `demo1234`. Si no, pulsa **Registrarse** y crea tu cuenta.

---

## Comandos útiles

```powershell
docker compose logs -f          # ver logs en tiempo real
docker compose ps               # estado de los contenedores
docker compose down             # parar todo
docker compose up -d --build    # reconstruir y arrancar (tras cambiar código)
```

---

## Si algo falla

- **El frontend carga pero da error al hacer login** → casi siempre es Supabase:
  revisa los 3 valores de `backend/.env` y que ejecutaste `001` y `002`.
  Mira el detalle con `docker compose logs backend`.
- **`backend` se reinicia solo** → credenciales de Supabase mal puestas
  (sobre todo `SUPABASE_DB_URL`: revisa contraseña y que el puerto sea `6543`).
- **Puerto 3000 u 8000 ocupado** → cierra lo que lo use o cambia el puerto en
  `docker-compose.yml` (ej. `"3001:80"`).
- **Cambiaste `backend/.env`** → reinícialo: `docker compose up -d` otra vez
  (Docker recoge el nuevo `.env` al recrear el contenedor).

---

## ¿Prefieres sin Docker? (no recomendado aquí)

Tu Python es **3.14** y el backend fija versiones de 2024 que no compilan en 3.14
(`psycopg2`, `pydantic-core`). Para correr local sin Docker tendrías que instalar
**Python 3.12** y crear el venv con él. Docker es más sencillo y ya está listo.
