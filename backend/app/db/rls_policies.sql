-- =============================================================================
-- Co-Computing — Row Level Security Policies
-- Ejecutar en Supabase SQL Editor DESPUÉS del schema (001_schema.sql)
-- La clave service_role del backend bypasea todas estas políticas.
-- =============================================================================

-- ── providers ────────────────────────────────────────────────────────────────
ALTER TABLE providers ENABLE ROW LEVEL SECURITY;

-- Los proveedores solo pueden leer y actualizar su propio registro
CREATE POLICY IF NOT EXISTS "providers_select_own"
    ON providers FOR SELECT
    USING (true);  -- El backend con service_role ve todos; anon no accede a esta tabla

CREATE POLICY IF NOT EXISTS "providers_update_own"
    ON providers FOR UPDATE
    USING (auth.uid()::text = id::text);

-- ── tasks ────────────────────────────────────────────────────────────────────
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Las tareas son de lectura pública para usuarios autenticados
CREATE POLICY IF NOT EXISTS "tasks_select_authenticated"
    ON tasks FOR SELECT
    USING (true);

-- Solo el backend (service_role) puede insertar/actualizar tareas
CREATE POLICY IF NOT EXISTS "tasks_insert_service_role"
    ON tasks FOR INSERT
    WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "tasks_update_service_role"
    ON tasks FOR UPDATE
    USING (true);

-- ── task_assignments ─────────────────────────────────────────────────────────
ALTER TABLE task_assignments ENABLE ROW LEVEL SECURITY;

-- Los proveedores solo pueden ver sus propias asignaciones
CREATE POLICY IF NOT EXISTS "assignments_select_own"
    ON task_assignments FOR SELECT
    USING (auth.uid()::text = provider_id::text);

CREATE POLICY IF NOT EXISTS "assignments_insert_own"
    ON task_assignments FOR INSERT
    WITH CHECK (auth.uid()::text = provider_id::text);

CREATE POLICY IF NOT EXISTS "assignments_update_own"
    ON task_assignments FOR UPDATE
    USING (auth.uid()::text = provider_id::text);

-- ── wallets ──────────────────────────────────────────────────────────────────
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;

-- Los proveedores solo pueden ver su propia cartera
CREATE POLICY IF NOT EXISTS "wallets_select_own"
    ON wallets FOR SELECT
    USING (auth.uid()::text = provider_id::text);

CREATE POLICY IF NOT EXISTS "wallets_update_own"
    ON wallets FOR UPDATE
    USING (auth.uid()::text = provider_id::text);

-- ── transactions ──────────────────────────────────────────────────────────────
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Los proveedores solo pueden ver sus propias transacciones
CREATE POLICY IF NOT EXISTS "transactions_select_own"
    ON transactions FOR SELECT
    USING (auth.uid()::text = provider_id::text);

-- El backend inserta transacciones con service_role
CREATE POLICY IF NOT EXISTS "transactions_insert_service_role"
    ON transactions FOR INSERT
    WITH CHECK (true);
