-- =============================================================================
-- Co-Computing — Migration 002: Row Level Security
-- PostgreSQL 15 (Supabase)
-- Ejecutar DESPUÉS de 001_schema.sql
-- =============================================================================
--
-- CONTEXTO IMPORTANTE:
-- El backend de Co-Computing utiliza autenticación JWT HS256 propia (FastAPI +
-- python-jose), NO Supabase Auth. Por tanto, la función auth.uid() de Supabase
-- NO devuelve el UUID del proveedor en las sesiones del backend.
--
-- El backend accede a la BD usando la SERVICE_ROLE KEY, que bypasea RLS de
-- forma controlada. Las políticas de usuario (auth.uid()) están aquí definidas
-- como ESTADO OBJETIVO para una posible migración futura a Supabase Auth o
-- acceso directo desde el cliente.
--
-- Para el MVP: la seguridad de acceso (proveedor A no accede a datos del
-- proveedor B) se garantiza al 100% en la capa de servicio de FastAPI
-- (app/services/task_lifecycle.py, comparando provider_id con el JWT propio).
--
-- =============================================================================

-- =============================================================================
-- ACTIVAR RLS EN LAS 5 TABLAS
-- =============================================================================
ALTER TABLE providers         ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks             ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets           ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_assignments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions      ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- POLÍTICAS PERMISIVAS PARA service_role (backend FastAPI)
-- El backend usa la service_role key → bypasea RLS automáticamente en Supabase.
-- Estas políticas son explícitas para documentar la intención y garantizar
-- compatibilidad si en algún momento se usa el rol service_role en contextos
-- donde RLS se aplica (ej. Supabase Edge Functions con service_role).
-- =============================================================================

-- --- providers ---
DROP POLICY IF EXISTS "service_role_all" ON providers;
CREATE POLICY "service_role_all" ON providers
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- --- tasks ---
DROP POLICY IF EXISTS "service_role_all" ON tasks;
CREATE POLICY "service_role_all" ON tasks
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- --- wallets ---
DROP POLICY IF EXISTS "service_role_all" ON wallets;
CREATE POLICY "service_role_all" ON wallets
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- --- task_assignments ---
DROP POLICY IF EXISTS "service_role_all" ON task_assignments;
CREATE POLICY "service_role_all" ON task_assignments
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- --- transactions ---
DROP POLICY IF EXISTS "service_role_all" ON transactions;
CREATE POLICY "service_role_all" ON transactions
    FOR ALL
    USING     (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- =============================================================================
-- POLÍTICAS DE USUARIO (Estado objetivo — requieren Supabase Auth activo)
-- Estas políticas se activan cuando auth.uid() devuelve el UUID del proveedor.
-- Con JWT propio (MVP actual) estas políticas no tienen efecto porque las
-- sesiones de usuario no pasan por Supabase Auth.
-- Están definidas aquí para facilitar la migración futura y como documentación
-- del modelo de seguridad deseado.
-- =============================================================================

-- --- providers: cada proveedor solo puede leer/actualizar su propio registro ---
DROP POLICY IF EXISTS "providers_select_own" ON providers;
CREATE POLICY "providers_select_own" ON providers
    FOR SELECT
    USING (auth.uid()::text = id::text);

DROP POLICY IF EXISTS "providers_update_own" ON providers;
CREATE POLICY "providers_update_own" ON providers
    FOR UPDATE
    USING     (auth.uid()::text = id::text)
    WITH CHECK (auth.uid()::text = id::text);

-- --- tasks: lectura pública para usuarios autenticados; escritura solo service_role ---
DROP POLICY IF EXISTS "tasks_select_authenticated" ON tasks;
CREATE POLICY "tasks_select_authenticated" ON tasks
    FOR SELECT
    USING (auth.role() IN ('authenticated', 'service_role'));

-- --- wallets: cada proveedor solo accede a su propia cartera ---
DROP POLICY IF EXISTS "wallets_select_own" ON wallets;
CREATE POLICY "wallets_select_own" ON wallets
    FOR SELECT
    USING (auth.uid()::text = provider_id::text);

DROP POLICY IF EXISTS "wallets_update_own" ON wallets;
CREATE POLICY "wallets_update_own" ON wallets
    FOR UPDATE
    USING     (auth.uid()::text = provider_id::text)
    WITH CHECK (auth.uid()::text = provider_id::text);

-- --- task_assignments: cada proveedor solo accede a sus propias asignaciones ---
DROP POLICY IF EXISTS "assignments_select_own" ON task_assignments;
CREATE POLICY "assignments_select_own" ON task_assignments
    FOR SELECT
    USING (auth.uid()::text = provider_id::text);

DROP POLICY IF EXISTS "assignments_insert_own" ON task_assignments;
CREATE POLICY "assignments_insert_own" ON task_assignments
    FOR INSERT
    WITH CHECK (auth.uid()::text = provider_id::text);

DROP POLICY IF EXISTS "assignments_update_own" ON task_assignments;
CREATE POLICY "assignments_update_own" ON task_assignments
    FOR UPDATE
    USING     (auth.uid()::text = provider_id::text)
    WITH CHECK (auth.uid()::text = provider_id::text);

-- --- transactions: cada proveedor solo puede leer sus propias transacciones ---
DROP POLICY IF EXISTS "transactions_select_own" ON transactions;
CREATE POLICY "transactions_select_own" ON transactions
    FOR SELECT
    USING (auth.uid()::text = provider_id::text);

-- =============================================================================
-- VERIFICACIÓN (consulta informativa, no ejecuta cambios)
-- Para comprobar que RLS está activo en todas las tablas:
--   SELECT tablename, rowsecurity
--   FROM pg_tables
--   WHERE schemaname = 'public'
--     AND tablename IN ('providers','tasks','wallets','task_assignments','transactions');
--
-- Para ver todas las políticas activas:
--   SELECT tablename, policyname, cmd, qual
--   FROM pg_policies
--   WHERE schemaname = 'public'
--   ORDER BY tablename, policyname;
-- =============================================================================
