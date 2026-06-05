# Encargo del cliente: MiniTareas (app de prueba)

## Objetivo de este encargo
App **pequeña y autocontenida** para **validar el equipo de agentes** de punta a
punta gastando poco. Toca todos los roles (backend, frontend, base de datos,
tests) pero con alcance mínimo.

## Resumen
**MiniTareas**: una lista de tareas personales con login. Cada usuario se registra,
inicia sesión y gestiona SUS tareas (crear, listar, marcar como hecha, borrar).

## Stack OBLIGATORIO (respetar al pie de la letra)
- **Backend:** FastAPI (Python) + Uvicorn.
- **Base de datos:** **SQLite** con SQLAlchemy. NADA de servicios externos
  (ni Supabase, ni Postgres, ni Docker para la DB). El fichero `app.db` se crea solo.
  Esto es importante: el QA debe poder ejecutar los tests SIN credenciales ni red.
- **Auth:** JWT simple (HS256), password hasheada con passlib/bcrypt. Secreto por
  variable de entorno con un valor por defecto para desarrollo.
- **Frontend:** React + Vite. En español.
- **Comunicación:** API REST JSON.

## Funcionalidades (todas obligatorias, y solo estas)
1. **Registro** — email + password (mín. 6). Devuelve error claro si el email ya existe.
2. **Login** — devuelve un JWT.
3. **Crear tarea** — título (texto). Queda asociada al usuario autenticado.
4. **Listar tareas** — solo las del usuario autenticado, más recientes primero.
5. **Marcar tarea como completada / no completada** — toggle.
6. **Borrar tarea** — solo si es del usuario.

## Modelo de datos (orientativo; el arquitecto lo detalla)
- **users**: id, email (único), password_hash, created_at.
- **tasks**: id, user_id (FK), title, is_done (bool, default false), created_at.

## Endpoints orientativos
- `POST /auth/register` → crea usuario.
- `POST /auth/login` → devuelve `{access_token, token_type}`.
- `GET /auth/me` → datos del usuario autenticado.
- `GET /tasks` → lista las tareas del usuario.
- `POST /tasks` → crea tarea `{title}`.
- `PATCH /tasks/{id}` → cambia `is_done`.
- `DELETE /tasks/{id}` → borra la tarea.

## Pantallas (frontend)
- **Login / Registro** (una pantalla con las dos opciones).
- **Mis tareas**: input para añadir, lista con checkbox (completar) y botón borrar,
  contador de pendientes. Estados claros: cargando, vacío, error.

## Requisitos de calidad
- Código de **producción**: completo, sin TODOs.
- Seguridad básica: password hasheada, JWT validado, un usuario no puede ver ni
  tocar tareas de otro, CORS para `http://localhost:5173`, sin secretos hardcodeados.
- **Tests del backend con pytest** que cubran: registro, login, crear tarea,
  listar (solo las propias), completar y borrar. Deben pasar ejecutando `pytest`
  sin configuración extra (SQLite en memoria o fichero temporal).
- READMEs claros para arrancar backend (`uvicorn`) y frontend (`npm run dev`).

## Fuera de alcance
- Recuperación de contraseña, roles, compartir tareas, etiquetas, fechas límite.
- Despliegue real (el DevOps deja Dockerfile/compose, pero no se despliega).
- App móvil.
