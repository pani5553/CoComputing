# Encargo: Publicar en Vercel + botón "Añadir créditos" (feature sobre Co-Computing)

## ⚠️ CONTEXTO — dos retoques pequeños sobre el proyecto existente
Co-Computing **ya funciona en local con Docker** y ya tiene toda la documentación de
despliegue (`DEPLOY.md`, `frontend/vercel.json`, brief `04-deploy-landing.md`). Este
encargo son dos retoques puntuales, **no** una feature grande. **No rompas** nada de
lo existente. Antes de tocar algo, **LEE**: `DEPLOY.md`, `frontend/src/pages/WalletPage.tsx`,
`frontend/src/pages/client/DepositPage.tsx`, `backend/app/main.py` (CORS/ENVIRONMENT).

## Importante sobre el alcance
Como en el brief de deploy anterior: los agentes **preparan y verifican**, el
**despliegue real** (crear cuenta en Vercel/Railway, importar el repo, pegar las
variables de entorno) lo hace el usuario — no hay credenciales para hacerlo de forma
autónoma.

## Qué hay que producir, por rol

### Frontend Dev
- **Botón "Añadir créditos"** en `WalletPage.tsx` (cartera del proveedor), junto a
  "Solicitar retiro". Al pulsarlo, abre un `Modal` (reutiliza el componente existente)
  con un mensaje tipo "Muy pronto podrás comprar créditos. Función en construcción." y
  un botón para cerrar. **Sin llamada a la API, sin endpoint nuevo, sin estado nuevo** —
  es solo UI de cara a futuro.
  - Ojo: esto es DISTINTO del flujo de recarga que ya existe para el cliente en
    `pages/client/DepositPage.tsx` (`POST /wallet/deposit`, brief 03). No los mezcles,
    no dupliques lógica, no toques esa pantalla.
- Repasa que el `npm run build` de producción compile sin errores con todas las
  pantallas actuales (dashboard, tareas, cómputo, cliente) — corrige cualquier error
  de tipos o import que encuentres.

### DevOps
- Repasa `DEPLOY.md` y `frontend/vercel.json` contra el estado actual del código
  (han cambiado cosas desde el brief 04: feature de cómputo, lado cliente). Corrige
  lo que haya quedado desactualizado.
- Confirma que la lista de variables de entorno de Railway en `DEPLOY.md` sigue
  completa — en particular `SUPABASE_DB_URL`, cuya ausencia rompe en silencio (error
  de conexión a socket local) todo lo que usa psycopg2 directo (escrow del cliente,
  jobs de cómputo). Ya está documentada; verifica que sigue correcta y visible en el
  checklist.
- Actualiza el checklist final de `DEPLOY.md` con cualquier ruta nueva a probar
  (`/cliente/*`, `/jobs/*`).

### Backend Dev
- Sin cambios de funcionalidad esperados. Solo confirma que `ENVIRONMENT=production`
  sigue desactivando `/docs`/`/redoc`, y que CORS lee el dominio del entorno (sin
  wildcard). Si algo quedó hardcodeado a `localhost`, arréglalo.

### QA
- Verifica que el build de producción del frontend (`npm run build`) y la imagen
  Docker del backend salen sin errores. Prueba manualmente el botón "Añadir créditos"
  (abre/cierra el modal, no rompe el resto de la página). No hacen falta tests
  automáticos nuevos.

### Tech Writer
- Actualiza `DEPLOY.md` con los hallazgos de DevOps.
- Añade una línea en `README.md` (funcionalidades o roadmap) indicando que
  "Añadir créditos" es un placeholder pendiente de integración de pagos reales.

### Roles con poco que hacer aquí
- **Product Owner / Architect**: confirman en 1 párrafo que no hay nada bloqueante
  para publicar. **Database Engineer**: confirma que las migraciones 001-005 están
  todas listadas en el checklist de despliegue. **Security**: repasa que
  `docs/06-security.md` sigue vigente sin cambios necesarios.

## Fuera de alcance
- Integración de pago real (Stripe, PayPal, cripto) para el botón de créditos.
- Crear las cuentas de Vercel/Railway o pegar las variables reales — lo hace el
  usuario siguiendo `DEPLOY.md`.
- Dominio propio, CDN, autoescalado, multi-región (ya excluido en el brief 04).
