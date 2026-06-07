# Encargo: Cómputo Real Distribuido (feature sobre Co-Computing)

## ⚠️ CONTEXTO — esto es una EXTENSIÓN, no un proyecto nuevo
Co-Computing **ya existe y funciona** (backend FastAPI, frontend React+TS+Zustand+
Tailwind, Supabase). Esta feature **AÑADE** cómputo real sobre lo que ya hay.
**NO reescribas ni rompas lo existente.** Antes de tocar nada, **LEE**:
- `docs/04-arquitectura.md`, `docs/04-api-contracts.md`, `docs/04-estructura.md`
- `backend/app/` (routers, services, db/queries, models)
- `frontend/src/` (pages, store, api, components)
- `migrations/001_schema.sql` (tablas existentes: providers, tasks, task_assignments, wallets, transactions)

## Problema que resolvemos
Hoy el "procesamiento" de una tarea es una **barra de progreso simulada**
(`backend/app/services/progress_service.py` calcula el % por tiempo transcurrido).
**No se ejecuta ningún cómputo real.** Queremos que el trabajo se procese DE VERDAD,
de forma distribuida y verificable.

## Objetivo
Permitir que:
1. Un usuario **suba un trabajo real** (un "job").
2. El sistema lo **trocee** en fragmentos (chunks).
3. Varios proveedores (workers) **procesen los fragmentos REALMENTE en su máquina**.
4. Los resultados se **validen por consenso**.
5. Se **pague** a los proveedores en CC y se actualice su **trust score**.

## Stack (respetar el existente)
- Backend: FastAPI + Supabase (mismo patrón que el código actual).
- Frontend: React 18 + TS + Zustand + Tailwind (mismos componentes UI ya creados).
- Worker: proceso Python independiente que habla con la API por HTTP (httpx).

## Caso de uso inicial: `data-processing` (cómputo real y ligero)
Para que el worker se pueda ejecutar sin modelos pesados, el primer tipo de job es
**procesamiento de datos**:
- El cliente sube un **CSV** (o pide generar un dataset) + una **operación**
  (ej: media/suma/min/max/conteo por columna, o filtrado+agregación).
- El sistema trocea el dataset **por filas** en N chunks.
- Cada worker calcula el resultado **real** de su chunk (usa **polars** o pandas).
- Se combinan los resultados parciales en el resultado final (reduce).
- **El worker se diseña como PLUGIN** (`WorkerTask` con una interfaz `process(payload)->result`)
  para poder añadir tipos futuros (`transcription`, `rendering`, `hashing`) sin tocar el núcleo.

## Modelo de datos nuevo — migración `migrations/004_compute.sql`
**No modifiques las tablas existentes.** Crea tablas nuevas:
- `jobs`: id, client_id (FK providers), job_type, status
  (`pending|splitting|processing|validating|completed|failed`), params (jsonb),
  total_chunks, completed_chunks, reward_total, result (jsonb), created_at, completed_at.
- `chunks`: id, job_id (FK), chunk_index, payload (jsonb/text), status
  (`pending|assigned|done|rejected`), assigned_to (FK providers, nullable),
  attempts, replicas_needed (default 2), created_at.
- `chunk_results`: id, chunk_id (FK), provider_id (FK), result (jsonb), duration_ms,
  is_valid (bool, nullable), created_at.
- Índices por job_id, status y assigned_to. RLS coherente con el patrón de `002_rls.sql`.

## Endpoints nuevos (backend) — nuevo router `compute`
Lado cliente:
- `POST /jobs` — crea un job (job_type, params, datos o CSV). Trocea en chunks.
- `GET /jobs` — lista mis jobs.
- `GET /jobs/{id}` — estado del job (con progreso real = chunks done / total).
- `GET /jobs/{id}/result` — resultado consolidado cuando está `completed`.

Lado worker:
- `POST /work/claim` — un worker reclama hasta N chunks `pending` (asignación atómica,
  respetando `replicas_needed`: el mismo chunk puede ir a 2 proveedores distintos).
- `POST /work/{chunk_id}/submit` — el worker entrega su resultado.

Lógica de cierre: cuando todos los chunks de un job están **validados**, marcar el job
`completed`, **consolidar** el resultado, **pagar** a los proveedores en CC (usar el
`wallet_service`/`transactions` existentes) y **actualizar el trust score** (usar
`trust_score` existente).

## El Worker — `backend/app/worker/`
Un proceso que:
1. Hace login como proveedor (reusa `/auth/login`).
2. Polling a `POST /work/claim`.
3. Ejecuta el cómputo **REAL** del chunk según `job_type` (mediante el plugin).
4. Sube el resultado con `POST /work/{chunk_id}/submit`.
- CLI: `python -m app.worker --api http://localhost:8000 --email X --password Y`.
- Incluye un script para levantar **varios workers** a la vez (demo de distribución).

## Validación por consenso
- Cada chunk se asigna a **2 proveedores** (`replicas_needed=2`).
- Cuando hay 2 resultados: si **coinciden** → ambos `is_valid=true`, chunk `done`.
- Si **no coinciden** → asignar a un 3º como desempate (mayoría).
- Solo se paga por resultados válidos. Un resultado inválido baja el trust.

## Frontend (nuevas pantallas, sin romper las actuales)
- **Cliente:** "Nuevo trabajo" (subir CSV + elegir operación) y "Mis trabajos"
  (lista con estado real y resultado). Reusa los componentes UI existentes (Card,
  Button, ProgressBar, etc.) y el patrón de `store/` y `api/`.
- **Proveedor:** que el progreso de procesamiento muestre **chunks reales** procesándose
  (puede integrarse con la pantalla de procesamiento existente).

## Integración con lo existente (obligatorio)
- Reusa: auth/JWT, `wallet_service` (pagar en CC), `trust_score`, componentes UI,
  stores Zustand y el cliente `api/`.
- Respeta los contratos de API actuales: **no cambies** los endpoints existentes.

## Calidad (esto es clave — que NO se repitan los bugs)
- Tests **reales** que ejerciten la lógica de verdad (no solo mocking de la BD):
  crear job → trocear → 2 workers procesan un chunk → validar consenso → pagar.
- Verifica que `tsc`/build del frontend pasa (incluye los tipos nuevos).
- **No rompas** los tests existentes ni el arranque con Docker.

## Fuera de alcance (por ahora)
- Transcripción de audio / render / ML pesado → dejar el worker **preparado como plugin**
  pero implementar **solo** `data-processing`.
- Pagos con dinero real (sigue siendo CC interno).
- Sandboxing/aislamiento de seguridad del worker (documenta el riesgo en seguridad).
