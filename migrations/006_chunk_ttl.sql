-- =============================================================================
-- Co-Computing — Migration 006: TTL de asignación de chunks
-- PostgreSQL 15 (Supabase)
-- Ejecutar DESPUÉS de 001_schema.sql .. 005_client.sql
-- =============================================================================

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS assigned_at timestamptz;

COMMENT ON COLUMN chunks.assigned_at IS
    'Timestamp de la asignación vigente. NULL si status != assigned (invariante mantenida por la aplicación, no por constraint). Usado por el reclamo perezoso: un chunk assigned cuyo assigned_at supere el TTL (10 min, ver compute_queries.CHUNK_ASSIGNMENT_TTL_MINUTES) se devuelve a pending en la siguiente llamada a POST /work/claim.';

CREATE INDEX IF NOT EXISTS idx_chunks_assigned_at
    ON chunks (assigned_at)
    WHERE status = 'assigned';
