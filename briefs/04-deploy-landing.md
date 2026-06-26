# Encargo: Deploy online + Landing (feature sobre Co-Computing)

## ⚠️ CONTEXTO — extensión sobre el proyecto existente
Co-Computing **ya funciona en local con Docker** (backend FastAPI, frontend React+TS,
Supabase en la nube). Objetivo de esta fase: **dejarlo listo para publicarlo en internet**
y crear una **landing page** pública. **No rompas** el funcionamiento local actual.
Antes de tocar nada, **LEE**: `docs/04-*`, `frontend/src/`, `deploy/`, `docker-compose.yml`,
`backend/app/main.py` (CORS y `ENVIRONMENT`).

## Importante sobre el alcance
Los agentes **preparan** todo lo necesario (landing, configs, guías). El **despliegue real**
(crear cuentas, conectar el repo, meter secretos) lo hará el usuario siguiendo la guía,
porque requiere sus cuentas. **No** se despliega de forma autónoma.

## Qué hay que producir, por rol

### Frontend Dev — Landing page pública (`frontend/`)
- Una **landing** en la ruta pública `/` (antes del login): hero con propuesta de valor
  ("Monetiza tu CPU/GPU"), sección "cómo funciona" (3 pasos), beneficios, y CTA a
  **Registrarse / Entrar**. En español, reusando Tailwind y los componentes existentes.
- La app autenticada pasa a `/app` (o mantener el routing actual tras login). No rompas
  las rutas existentes; solo añade la landing delante.
- Responsive (que se vea bien en móvil).

### DevOps — Configs de despliegue (`deploy/`, raíz)
- **Frontend en Vercel**: `vercel.json` (rewrites para SPA), build de Vite, doc de qué
  variable poner (`VITE_API_URL` → URL del backend en prod).
- **Backend en Railway** (o Render/Fly): config para construir con `deploy/backend.Dockerfile`,
  puerto, comando de arranque, healthcheck. Lista de variables de entorno de producción.
- Asegurar que el backend lee `FRONTEND_URL` (CORS) y `ENVIRONMENT` desde el entorno.

### Backend Dev — Ajustes de producción (`backend/`)
- Verificar/ajustar que `ENVIRONMENT=production` **desactiva** `/docs`, `/redoc`, `/openapi.json`
  (ya debería) y sube el log level.
- CORS configurable por entorno (sin `*`), aceptando el dominio del frontend de prod.
- No hardcodear secretos; todo por variables de entorno.

### Security — Checklist de producción (`docs/06-security.md`, añadir sección)
- Secretos solo en el panel del hosting (nunca en el repo), `service_role` solo en backend,
  `/docs` apagado en prod, CORS sin wildcard, JWT secret fuerte, `sslmode=require` en la BD.

### Tech Writer — Guías (`DEPLOY.md` en la raíz, y `docs/07-*`)
- **`DEPLOY.md`**: guía paso a paso para publicar: (1) Vercel: crear cuenta, importar repo,
  carpeta `frontend`, variable `VITE_API_URL`; (2) Railway: nuevo proyecto desde el repo,
  Dockerfile del backend, variables de entorno; (3) conectar las dos URLs; (4) checklist final.
- **Guion de vídeo demo** (1-2 min): qué mostrar (registro → ver tareas → aceptar → procesar
  → cartera) para enseñar el proyecto en portfolio.

### Roles con poco que hacer aquí
- **Product Owner**: define en 1 párrafo el objetivo de esta fase (publicar + landing) y los
  criterios de "hecho". **Architect**: decide hosting y cómo encaja (1 doc breve).
- **Database Engineer**: no hay cambios de BD → confírmalo y pasa.
- **QA**: verifica que el **build de producción** del frontend (`npm run build`) y el del
  backend (imagen Docker) salen sin errores. No hace falta nuevos tests de lógica.

## Fuera de alcance
- Dominio propio / DNS / certificados personalizados (usar los subdominios gratuitos de
  Vercel/Railway).
- CDN avanzado, autoescalado, multi-región.
- Grabar el vídeo (eso lo hace el usuario; aquí solo el guion).
