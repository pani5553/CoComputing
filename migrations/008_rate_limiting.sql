-- =============================================================================
-- Co-Computing — Migration 008: Rate limiting compartido (SEC-02, SEC-21)
-- PostgreSQL 15 (Supabase)
-- Ejecutar DESPUÉS de 001_schema.sql .. 007_chunk_abandon_tracking.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS rate_limit_counters (
    bucket        text        NOT NULL,
    window_start  timestamptz NOT NULL,
    request_count integer     NOT NULL DEFAULT 0,
    PRIMARY KEY (bucket, window_start)
);

COMMENT ON TABLE rate_limit_counters IS
    'Contador de peticiones por bucket y ventana fija para rate limiting compartido entre procesos Uvicorn. Ver docs/04-arquitectura.md §15.1.';
