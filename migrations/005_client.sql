-- =============================================================================
-- Co-Computing — Migration 005: Lado Cliente
-- PostgreSQL 15 (Supabase)
-- Idempotente: usa IF NOT EXISTS, ALTER...IF NOT EXISTS, DROP CONSTRAINT ... IF EXISTS
-- =============================================================================

-- =============================================================================
-- 1. Añadir client_id a tasks (nullable — las filas del seed quedan sin cliente)
-- =============================================================================
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS client_id uuid REFERENCES providers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_client_id
    ON tasks (client_id)
    WHERE client_id IS NOT NULL;

-- =============================================================================
-- 2. Ampliar tx_type en transactions para operaciones de cliente
-- Los nuevos tipos: deposito, escrow, reembolso, pago_recibido
-- Supabase/PostgreSQL: hay que DROP y re-CREATE el constraint (ALTER no soporta
-- añadir valores a CHECK directamente).
-- =============================================================================
ALTER TABLE transactions
    DROP CONSTRAINT IF EXISTS transactions_tx_type_values;

ALTER TABLE transactions
    ADD CONSTRAINT transactions_tx_type_values
        CHECK (tx_type IN (
            'pago_tarea',
            'retiro',
            'bonus',
            'penalizacion',
            'deposito',
            'escrow',
            'reembolso',
            'pago_recibido'
        ));

-- =============================================================================
-- 3. Tabla escrows — retención de fondos por tarea publicada
-- Un registro por tarea; amount_released crece conforme los proveedores completan.
-- =============================================================================
CREATE TABLE IF NOT EXISTS escrows (
    id               uuid          NOT NULL DEFAULT gen_random_uuid(),
    task_id          uuid          NOT NULL,
    client_id        uuid          NOT NULL,
    amount_per_slot  numeric(10,2) NOT NULL,
    total_slots      integer       NOT NULL,
    amount_held      numeric(12,2) NOT NULL,
    amount_released  numeric(12,2) NOT NULL DEFAULT 0.00,
    status           text          NOT NULL DEFAULT 'activo',
    created_at       timestamptz   NOT NULL DEFAULT now(),
    updated_at       timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT escrows_pkey PRIMARY KEY (id),
    CONSTRAINT escrows_task_id_unique UNIQUE (task_id),
    CONSTRAINT escrows_task_fkey
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
    CONSTRAINT escrows_client_fkey
        FOREIGN KEY (client_id) REFERENCES providers(id) ON DELETE RESTRICT,
    CONSTRAINT escrows_amount_per_slot_positive
        CHECK (amount_per_slot > 0),
    CONSTRAINT escrows_total_slots_positive
        CHECK (total_slots > 0),
    CONSTRAINT escrows_amount_held_non_negative
        CHECK (amount_held >= 0),
    CONSTRAINT escrows_amount_released_non_negative
        CHECK (amount_released >= 0),
    CONSTRAINT escrows_released_lte_held
        CHECK (amount_released <= amount_held),
    CONSTRAINT escrows_status_values
        CHECK (status IN ('activo', 'cancelado', 'completado'))
);

DROP TRIGGER IF EXISTS trg_escrows_updated_at ON escrows;
CREATE TRIGGER trg_escrows_updated_at
    BEFORE UPDATE ON escrows
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_escrows_client_id
    ON escrows (client_id);

CREATE INDEX IF NOT EXISTS idx_escrows_status
    ON escrows (status);

-- =============================================================================
-- 4. RLS en escrows (coherente con 002_rls.sql — service_role bypasses RLS)
-- =============================================================================
ALTER TABLE escrows ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "escrows_service_role_all" ON escrows;
CREATE POLICY "escrows_service_role_all"
    ON escrows
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- COMENTARIOS
-- =============================================================================
COMMENT ON TABLE escrows IS
    'Retención de CC del cliente al publicar una tarea. amount_held = reward * total_slots. amount_released += reward cada vez que un proveedor completa la tarea.';
COMMENT ON COLUMN escrows.amount_per_slot IS
    'Recompensa por plaza = tasks.reward al momento de crear la tarea.';
COMMENT ON COLUMN escrows.amount_released IS
    'Suma acumulada pagada a proveedores desde este escrow. Incrementado en complete_task.';
COMMENT ON COLUMN escrows.status IS
    'activo: fondos retenidos. cancelado: tarea cancelada y reembolso emitido. completado: todas las plazas completadas.';
