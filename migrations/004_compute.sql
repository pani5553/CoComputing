-- =============================================================================
-- Co-Computing — Migration 004: Compute Pipeline
-- PostgreSQL 15 (Supabase)
-- Ejecutar DESPUÉS de 001_schema.sql, 002_rls.sql y 003_seed.sql
-- Idempotente: usa CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS,
--              DROP POLICY IF EXISTS antes de CREATE POLICY
-- =============================================================================
--
-- CONTEXTO:
-- Esta migración introduce el pipeline de cómputo distribuido:
--   jobs        → trabajos de alto nivel enviados por un cliente (provider con rol cliente)
--   chunks      → fragmentos en los que el backend divide cada job
--   chunk_results → resultados individuales que cada proveedor devuelve por chunk
--
-- El backend (FastAPI + service_role key) gestiona todo el ciclo de vida.
-- auth.uid() NO está disponible en sesiones del backend (JWT HS256 propio).
-- La seguridad de acceso se garantiza en la capa de servicio de FastAPI.
-- Las políticas de usuario se definen como estado objetivo para migración futura.
--
-- =============================================================================

-- =============================================================================
-- TABLA 1: jobs
-- Orden de creación: primero (FK → providers únicamente)
-- =============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id               uuid           NOT NULL DEFAULT gen_random_uuid(),
    client_id        uuid           NOT NULL,
    job_type         text           NOT NULL,
    status           text           NOT NULL DEFAULT 'pending',
    params           jsonb          NOT NULL DEFAULT '{}',
    total_chunks     integer        NOT NULL DEFAULT 0,
    completed_chunks integer        NOT NULL DEFAULT 0,
    reward_total     numeric(10,2)  NOT NULL DEFAULT 0.00,
    result           jsonb,
    created_at       timestamptz    NOT NULL DEFAULT now(),
    completed_at     timestamptz,

    CONSTRAINT jobs_pkey PRIMARY KEY (id),
    CONSTRAINT jobs_client_fkey
        FOREIGN KEY (client_id) REFERENCES providers(id) ON DELETE RESTRICT,
    CONSTRAINT jobs_job_type_values
        CHECK (job_type IN ('data-processing')),
    CONSTRAINT jobs_status_values
        CHECK (status IN ('pending', 'splitting', 'processing', 'validating', 'completed', 'failed')),
    CONSTRAINT jobs_total_chunks_non_negative
        CHECK (total_chunks >= 0),
    CONSTRAINT jobs_completed_chunks_non_negative
        CHECK (completed_chunks >= 0),
    CONSTRAINT jobs_completed_chunks_lte_total
        CHECK (completed_chunks <= total_chunks),
    CONSTRAINT jobs_reward_total_non_negative
        CHECK (reward_total >= 0.00)
);

-- Nota: jobs no tiene columna updated_at; el backend actualiza status y
-- completed_at directamente. No se crea trigger set_updated_at aquí.

-- Índice: búsqueda de jobs por cliente (dashboard del cliente)
CREATE INDEX IF NOT EXISTS idx_jobs_client_id
    ON jobs (client_id);

-- Índice: filtrado por estado (worker/scheduler del backend)
CREATE INDEX IF NOT EXISTS idx_jobs_status
    ON jobs (status);

-- Índice compuesto: jobs activos de un cliente (caso de uso más frecuente)
CREATE INDEX IF NOT EXISTS idx_jobs_client_status
    ON jobs (client_id, status);

-- Comentarios
COMMENT ON TABLE jobs IS
    'Trabajos de cómputo de alto nivel enviados por un cliente. El backend los divide en chunks para distribuirlos entre proveedores.';
COMMENT ON COLUMN jobs.params IS
    'Para data-processing: {"operation":"mean","columns":["col1"]}. Extensible para futuros job_types.';
COMMENT ON COLUMN jobs.result IS
    'Resultado consolidado tras reducir todos los chunk_results válidos. NULL mientras el job no esté completed.';
COMMENT ON COLUMN jobs.total_chunks IS
    'Número total de chunks en que se ha dividido el job. Fijado por el backend durante la fase splitting.';
COMMENT ON COLUMN jobs.completed_chunks IS
    'Número de chunks ya validados y consolidados. Incrementado atómicamente por el backend al validar cada chunk.';
COMMENT ON COLUMN jobs.reward_total IS
    'Recompensa total del job en CCT. Distribuida entre los proveedores que procesen chunks válidos.';
COMMENT ON COLUMN jobs.completed_at IS
    'Timestamp en que el job alcanzó el estado completed o failed. NULL mientras está en curso.';

-- =============================================================================
-- TABLA 2: chunks
-- Orden de creación: segundo (FK → jobs, providers)
-- =============================================================================
CREATE TABLE IF NOT EXISTS chunks (
    id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    job_id          uuid        NOT NULL,
    chunk_index     integer     NOT NULL,
    payload         jsonb       NOT NULL,
    status          text        NOT NULL DEFAULT 'pending',
    assigned_to     uuid,
    attempts        integer     NOT NULL DEFAULT 0,
    replicas_needed integer     NOT NULL DEFAULT 2,
    created_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT chunks_pkey PRIMARY KEY (id),
    CONSTRAINT chunks_job_chunk_unique UNIQUE (job_id, chunk_index),
    CONSTRAINT chunks_job_fkey
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    CONSTRAINT chunks_assigned_to_fkey
        FOREIGN KEY (assigned_to) REFERENCES providers(id) ON DELETE SET NULL,
    CONSTRAINT chunks_chunk_index_non_negative
        CHECK (chunk_index >= 0),
    CONSTRAINT chunks_status_values
        CHECK (status IN ('pending', 'assigned', 'done', 'rejected')),
    CONSTRAINT chunks_attempts_non_negative
        CHECK (attempts >= 0),
    CONSTRAINT chunks_replicas_needed_positive
        CHECK (replicas_needed >= 1)
);

-- Índice: todos los chunks de un job (carga del scheduler)
CREATE INDEX IF NOT EXISTS idx_chunks_job_id
    ON chunks (job_id);

-- Índice: chunks por estado (scheduler selecciona pending/rejected)
CREATE INDEX IF NOT EXISTS idx_chunks_status
    ON chunks (status);

-- Índice compuesto: chunks de un job filtrados por estado
CREATE INDEX IF NOT EXISTS idx_chunks_job_status
    ON chunks (job_id, status);

-- Índice parcial: chunks asignados a un proveedor concreto (solo filas con valor)
CREATE INDEX IF NOT EXISTS idx_chunks_assigned_to
    ON chunks (assigned_to)
    WHERE assigned_to IS NOT NULL;

-- Comentarios
COMMENT ON TABLE chunks IS
    'Fragmentos en que el backend divide un job para distribución entre proveedores. Cada chunk es procesado de forma independiente.';
COMMENT ON COLUMN chunks.payload IS
    'Para data-processing: {"rows": [[...],[...]], "columns":["col1","col2"]}';
COMMENT ON COLUMN chunks.chunk_index IS
    'Posición ordinal del chunk dentro del job. Empieza en 0. Junto a job_id forma clave única.';
COMMENT ON COLUMN chunks.assigned_to IS
    'UUID del proveedor actualmente asignado a procesar este chunk. NULL si está pending o rejected.';
COMMENT ON COLUMN chunks.attempts IS
    'Número de veces que se ha intentado procesar este chunk. Incrementado por el scheduler en cada asignación.';
COMMENT ON COLUMN chunks.replicas_needed IS
    'Número de proveedores distintos que deben procesar este chunk para validación por consenso. Default 2.';

-- =============================================================================
-- TABLA 3: chunk_results
-- Orden de creación: tercero (FK → chunks, providers)
-- =============================================================================
CREATE TABLE IF NOT EXISTS chunk_results (
    id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    chunk_id    uuid        NOT NULL,
    provider_id uuid        NOT NULL,
    result      jsonb       NOT NULL,
    duration_ms integer     NOT NULL,
    is_valid    boolean,
    created_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT chunk_results_pkey PRIMARY KEY (id),
    CONSTRAINT chunk_results_chunk_provider_unique UNIQUE (chunk_id, provider_id),
    CONSTRAINT chunk_results_chunk_fkey
        FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE,
    CONSTRAINT chunk_results_provider_fkey
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE RESTRICT,
    CONSTRAINT chunk_results_duration_ms_positive
        CHECK (duration_ms > 0)
);

-- Índice: todos los resultados de un chunk (validación por consenso)
CREATE INDEX IF NOT EXISTS idx_chunk_results_chunk_id
    ON chunk_results (chunk_id);

-- Índice: historial de resultados de un proveedor (dashboard, métricas)
CREATE INDEX IF NOT EXISTS idx_chunk_results_provider_id
    ON chunk_results (provider_id);

-- Índice compuesto: resultados de un chunk filtrados por validez (consolidación)
CREATE INDEX IF NOT EXISTS idx_chunk_results_is_valid
    ON chunk_results (chunk_id, is_valid);

-- Comentarios
COMMENT ON TABLE chunk_results IS
    'Resultados individuales entregados por los proveedores para cada chunk. Múltiples proveedores pueden entregar resultado del mismo chunk (validación por consenso).';
COMMENT ON COLUMN chunk_results.result IS
    'Resultado real del cómputo para este chunk. Estructura espejo a chunks.payload pero con los valores calculados.';
COMMENT ON COLUMN chunk_results.duration_ms IS
    'Tiempo de procesamiento en milisegundos reportado por el proveedor. Debe ser mayor que 0.';
COMMENT ON COLUMN chunk_results.is_valid IS
    'NULL=pendiente de validación por consenso. true=válido (coincide con la mayoría). false=rechazado.';

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

-- --- Activar RLS en las 3 tablas nuevas ---
ALTER TABLE jobs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks        ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunk_results ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- POLÍTICAS PERMISIVAS PARA service_role (backend FastAPI)
-- El backend usa la service_role key → bypasea RLS automáticamente en Supabase.
-- Se definen explícitamente para documentar la intención y garantizar
-- compatibilidad con contextos donde RLS se aplica (ej. Edge Functions).
-- =============================================================================

-- --- jobs ---
DROP POLICY IF EXISTS "service_role_all" ON jobs;
CREATE POLICY "service_role_all" ON jobs
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- --- chunks ---
DROP POLICY IF EXISTS "service_role_all" ON chunks;
CREATE POLICY "service_role_all" ON chunks
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- --- chunk_results ---
DROP POLICY IF EXISTS "service_role_all" ON chunk_results;
CREATE POLICY "service_role_all" ON chunk_results
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- =============================================================================
-- POLÍTICAS DE USUARIO (Estado objetivo — requieren Supabase Auth activo)
-- Con JWT HS256 propio (MVP actual) estas políticas no tienen efecto porque
-- las sesiones del backend no pasan por Supabase Auth y auth.uid() es NULL.
-- Están definidas como documentación del modelo de seguridad deseado y para
-- facilitar migración futura a Supabase Auth o acceso directo desde cliente.
-- =============================================================================

-- --- jobs: el cliente solo ve y crea sus propios jobs ---
DROP POLICY IF EXISTS "jobs_select_own" ON jobs;
CREATE POLICY "jobs_select_own" ON jobs
    FOR SELECT
    USING (auth.uid()::text = client_id::text);

DROP POLICY IF EXISTS "jobs_insert_own" ON jobs;
CREATE POLICY "jobs_insert_own" ON jobs
    FOR INSERT
    WITH CHECK (auth.uid()::text = client_id::text);

-- --- chunks: accesibles para usuarios autenticados que tengan un job asociado ---
-- Simplificado: auth.uid() con JOIN a jobs es costoso en RLS; se permite a
-- cualquier usuario autenticado leer chunks (el acceso real lo filtra el backend).
DROP POLICY IF EXISTS "chunks_select_job_owner" ON chunks;
CREATE POLICY "chunks_select_job_owner" ON chunks
    FOR SELECT
    USING (auth.role() IN ('authenticated', 'service_role'));

-- --- chunk_results: cada proveedor solo accede a sus propios resultados ---
DROP POLICY IF EXISTS "chunk_results_select_own" ON chunk_results;
CREATE POLICY "chunk_results_select_own" ON chunk_results
    FOR SELECT
    USING (auth.uid()::text = provider_id::text);

DROP POLICY IF EXISTS "chunk_results_insert_own" ON chunk_results;
CREATE POLICY "chunk_results_insert_own" ON chunk_results
    FOR INSERT
    WITH CHECK (auth.uid()::text = provider_id::text);

-- =============================================================================
-- VERIFICACIÓN (consulta informativa, no ejecuta cambios)
-- Para comprobar que las tablas y RLS están activas:
--   SELECT tablename, rowsecurity
--   FROM pg_tables
--   WHERE schemaname = 'public'
--     AND tablename IN ('jobs','chunks','chunk_results');
--
-- Para ver todas las políticas de las tablas nuevas:
--   SELECT tablename, policyname, cmd, qual
--   FROM pg_policies
--   WHERE schemaname = 'public'
--     AND tablename IN ('jobs','chunks','chunk_results')
--   ORDER BY tablename, policyname;
-- =============================================================================
