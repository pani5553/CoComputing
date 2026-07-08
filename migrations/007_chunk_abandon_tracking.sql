-- =============================================================================
-- Co-Computing — Migration 007: Tracking de abandono de chunks (SEC-36)
-- PostgreSQL 15 (Supabase)
-- Ejecutar DESPUÉS de 001_schema.sql .. 006_chunk_ttl.sql
-- =============================================================================

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS abandoned_by uuid[] NOT NULL DEFAULT '{}';

COMMENT ON COLUMN chunks.abandoned_by IS
    'Provider_id que abandonaron este chunk: se añade el assigned_to vigente cada vez que el reclamo por TTL (ver migration 006 y compute_queries.claim_chunks_atomic, sentencia 1) devuelve el chunk a pending sin haber recibido submit. Se usa para excluir a ese proveedor de volver a reclamar el MISMO chunk en el futuro (mitigación de SEC-36 — abuso de claim/abandon repetido para forzar el rechazo tras MAX_CHUNK_ATTEMPTS sin penalización de trust). No se limpia al reasignar ni al rechazar el chunk.';

-- Sin índice nuevo: el array se consulta con `%(provider_id)s = ANY(c.abandoned_by)`
-- dentro del WHERE de la sentencia de claim (compute_queries.claim_chunks_atomic,
-- sentencia 3), que ya filtra primero por c.status = 'pending' usando el índice
-- existente idx_chunks_status. El universo de filas pending es pequeño y ya está
-- acotado por ese índice, así que un GIN sobre abandoned_by no aportaría selectividad
-- adicional relevante aquí; se puede añadir más adelante si el volumen de chunks
-- pending crece lo suficiente para justificarlo.
