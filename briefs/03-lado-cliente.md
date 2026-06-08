1# Encargo: Lado Cliente (feature sobre Co-Computing)

## ⚠️ CONTEXTO — esto es una EXTENSIÓN, no un proyecto nuevo
Co-Computing **ya existe y funciona** (backend FastAPI, frontend React+TS+Zustand+
Tailwind, Supabase). Esta feature **AÑADE** el lado cliente. **NO rompas lo existente.**
Antes de tocar nada, **LEE**:
- `docs/04-arquitectura.md`, `docs/04-api-contracts.md`, `docs/04-estructura.md`
- `backend/app/` (routers, services, db/queries, models) — fíjate en `tasks`, `wallet`, `trust`
- `frontend/src/` (pages, store, api, components)
- `migrations/001_schema.sql` (tablas: providers, tasks, task_assignments, wallets, transactions)

## Problema que resolvemos
Hoy las tareas del catálogo **vienen del seed** (`003_seed.sql`). **Nadie puede subir
tareas.** Solo existe el lado PROVEEDOR (que las consume). Falta el lado CLIENTE.

## Objetivo
Que un usuario pueda actuar como **cliente** y:
1. **Recargar** saldo en CC (depósito simulado, igual que el retiro ya es simulado).
2. **Crear y publicar** una tarea al catálogo (la que hoy sale del seed).
3. **Financiarla** con escrow: al publicarla se le **retiene** `recompensa × plazas` en CC.
4. **Seguir** sus tareas publicadas (plazas ocupadas, proveedores, completadas).
5. **Cancelar** una tarea y recuperar el CC retenido no usado.

## Stack (respetar el existente)
Backend FastAPI + Supabase; frontend React 18 + TS + Zustand + Tailwind (reusa los
componentes UI ya creados: Card, Button, Input, Modal, Badge, etc.).

## Modelo de datos — migración `migrations/005_client.sql`
**No modifiques tablas existentes salvo añadir columnas nullable.**
- Añadir a `tasks`: `client_id uuid` (FK providers, nullable — las del seed quedan sin cliente).
- Escrow: reutiliza `wallets` (`pending_balance` para lo retenido) y `transactions`
  (nuevos `tx_type`: `deposito`, `escrow`, `pago_recibido`/`reembolso`). Si hace falta,
  añade una tabla `escrows` (job/task_id, client_id, amount_held, amount_released).
- RLS coherente con `002_rls.sql`.

## Endpoints nuevos (backend)
- `POST /wallet/deposit` — recarga simulada de CC (suma a `available_balance` + transacción).
- `POST /client/tasks` — crea una tarea (título, tipo, descripción, recompensa, dificultad,
  hardware, plazas, duración). Valida saldo, **retiene** el escrow, publica al catálogo.
- `GET /client/tasks` — mis tareas publicadas, con estado (plazas usadas, nº asignaciones).
- `GET /client/tasks/{id}` — detalle: proveedores que la aceptaron/completaron.
- `POST /client/tasks/{id}/cancel` — cancela y **reembolsa** el escrow no consumido.

## Lógica de escrow/pagos (clave)
- Al **publicar**: retener `recompensa × plazas` del `available_balance` del cliente
  (mover a retenido). Si no hay saldo → 400.
- Cuando un **proveedor completa** una tarea (flujo `task_lifecycle.complete_task` ya
  existente): el pago al proveedor **sale del escrow del cliente** (no del aire).
  Integra esto SIN romper el flujo actual de `complete`.
- Al **cancelar**: reembolsar al cliente el escrow de las plazas no completadas.

## Frontend (nuevas pantallas, sin romper las actuales)
- **Recargar saldo** (modal o pantalla simple).
- **Publicar tarea** (formulario con todos los campos + coste total estimado del escrow).
- **Mis tareas publicadas** (lista con estado).
- **Detalle de tarea publicada** (asignaciones/proveedores).
- Añade navegación a estas pantallas (un apartado "Cliente" / "Publicar") reusando el
  layout/navbar existente. No toques las pantallas del proveedor salvo enlazar.

## Integración con lo existente (obligatorio)
- Las tareas creadas por el cliente **aparecen en el catálogo** que ya ven los proveedores
  (`GET /tasks/`), mezcladas con las del seed.
- Reusa auth/JWT, `wallet_service`, `transactions`, `trust_score`, componentes UI, stores y `api/`.
- **No cambies** los endpoints existentes (solo añade).

## Calidad (que no se repitan los bugs)
- Tests **reales** (no solo mocking): recargar → publicar tarea (escrow retenido) →
  un proveedor la completa (pago sale del escrow al proveedor) → cancelar (reembolso).
- Verifica que el build del frontend (`tsc`) pasa con los tipos nuevos.
- **No rompas** los tests existentes ni el arranque con Docker.

## Fuera de alcance (por ahora)
- Pagos con dinero real (sigue siendo CC interno; el depósito es simulado).
- KYC, facturación, disputas/reembolsos por calidad.
- Edición de tareas ya publicadas (solo crear y cancelar).
