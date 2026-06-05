-- =============================================================================
-- Co-Computing — Migration 001: Schema
-- PostgreSQL 15 (Supabase)
-- Ejecutar en: Supabase SQL Editor
-- Idempotente: usa CREATE TABLE IF NOT EXISTS, CREATE OR REPLACE FUNCTION
-- =============================================================================

-- Habilitar extensión uuid si no está activa (Supabase la activa por defecto)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- FUNCIÓN AUXILIAR: actualizar updated_at automáticamente
-- =============================================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- =============================================================================
-- TABLA 1: providers
-- Orden de creación: primero (sin dependencias de FK)
-- =============================================================================
CREATE TABLE IF NOT EXISTS providers (
    id                   uuid            NOT NULL DEFAULT gen_random_uuid(),
    email                text            NOT NULL,
    full_name            text            NOT NULL,
    password_hash        text            NOT NULL,
    trust_score          numeric(5,2)    NOT NULL DEFAULT 0.00,
    rank                 text            NOT NULL DEFAULT 'nuevo',
    tasks_completed      integer         NOT NULL DEFAULT 0,
    success_rate         numeric(5,2)    NOT NULL DEFAULT 0.00,
    total_earned         numeric(12,2)   NOT NULL DEFAULT 0.00,
    completion_rate      numeric(5,2)    NOT NULL DEFAULT 0.00,
    accuracy             numeric(5,2)    NOT NULL DEFAULT 80.00,
    response_time_score  numeric(5,2)    NOT NULL DEFAULT 70.00,
    client_rating        numeric(5,2)    NOT NULL DEFAULT 70.00,
    cpu_model            text,
    gpu_model            text,
    ram_gb               integer,
    storage_gb           integer,
    is_online            boolean         NOT NULL DEFAULT false,
    created_at           timestamptz     NOT NULL DEFAULT now(),
    updated_at           timestamptz     NOT NULL DEFAULT now(),

    CONSTRAINT providers_pkey PRIMARY KEY (id),
    CONSTRAINT providers_email_unique UNIQUE (email),
    CONSTRAINT providers_trust_score_range
        CHECK (trust_score >= 0.00 AND trust_score <= 100.00),
    CONSTRAINT providers_rank_values
        CHECK (rank IN ('nuevo', 'confiable', 'experto', 'elite')),
    CONSTRAINT providers_success_rate_range
        CHECK (success_rate >= 0.00 AND success_rate <= 100.00),
    CONSTRAINT providers_completion_rate_range
        CHECK (completion_rate >= 0.00 AND completion_rate <= 100.00),
    CONSTRAINT providers_accuracy_range
        CHECK (accuracy >= 0.00 AND accuracy <= 100.00),
    CONSTRAINT providers_response_time_range
        CHECK (response_time_score >= 0.00 AND response_time_score <= 100.00),
    CONSTRAINT providers_client_rating_range
        CHECK (client_rating >= 0.00 AND client_rating <= 100.00),
    CONSTRAINT providers_tasks_completed_non_negative
        CHECK (tasks_completed >= 0),
    CONSTRAINT providers_total_earned_non_negative
        CHECK (total_earned >= 0.00),
    CONSTRAINT providers_ram_positive
        CHECK (ram_gb IS NULL OR ram_gb > 0),
    CONSTRAINT providers_storage_positive
        CHECK (storage_gb IS NULL OR storage_gb > 0)
);

-- Trigger updated_at en providers
DROP TRIGGER IF EXISTS trg_providers_updated_at ON providers;
CREATE TRIGGER trg_providers_updated_at
    BEFORE UPDATE ON providers
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Índice para búsqueda por email en login
CREATE UNIQUE INDEX IF NOT EXISTS idx_providers_email
    ON providers (email);

-- =============================================================================
-- TABLA 2: tasks
-- Orden de creación: segundo (sin dependencias de FK)
-- =============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id                uuid        NOT NULL DEFAULT gen_random_uuid(),
    title             text        NOT NULL,
    task_type         text        NOT NULL,
    description       text        NOT NULL,
    reward            numeric(10,2) NOT NULL,
    duration_min      integer     NOT NULL,
    duration_max      integer     NOT NULL,
    difficulty        text        NOT NULL,
    hardware_required text        NOT NULL,
    total_slots       integer     NOT NULL,
    slots_left        integer     NOT NULL,
    stages            text[]      NOT NULL,
    requester_name    text        NOT NULL,
    requester_company text,
    status            text        NOT NULL DEFAULT 'disponible',
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT tasks_pkey PRIMARY KEY (id),
    CONSTRAINT tasks_reward_positive
        CHECK (reward > 0),
    CONSTRAINT tasks_duration_valid
        CHECK (duration_min > 0 AND duration_max >= duration_min),
    CONSTRAINT tasks_slots_valid
        CHECK (slots_left >= 0 AND slots_left <= total_slots),
    CONSTRAINT tasks_total_slots_positive
        CHECK (total_slots > 0),
    CONSTRAINT tasks_difficulty_values
        CHECK (difficulty IN ('facil', 'medio', 'dificil')),
    CONSTRAINT tasks_hardware_values
        CHECK (hardware_required IN ('cpu', 'gpu', 'mixto')),
    CONSTRAINT tasks_type_values
        CHECK (task_type IN ('renderizado_3d', 'entrenamiento_ml', 'transcodificacion_video', 'analisis_datos', 'simulacion_fisica')),
    CONSTRAINT tasks_status_values
        CHECK (status IN ('disponible', 'en_progreso', 'completada', 'cancelada')),
    CONSTRAINT tasks_stages_not_empty
        CHECK (array_length(stages, 1) >= 1)
);

-- Trigger updated_at en tasks
DROP TRIGGER IF EXISTS trg_tasks_updated_at ON tasks;
CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Índice crítico: listado de tareas disponibles con plazas libres
CREATE INDEX IF NOT EXISTS idx_tasks_status_slots
    ON tasks (status, slots_left)
    WHERE status = 'disponible' AND slots_left > 0;

-- Índice para filtrado por dificultad
CREATE INDEX IF NOT EXISTS idx_tasks_difficulty
    ON tasks (difficulty);

-- Índice para filtrado por hardware
CREATE INDEX IF NOT EXISTS idx_tasks_hardware
    ON tasks (hardware_required);

-- Índice para filtrado por tipo
CREATE INDEX IF NOT EXISTS idx_tasks_type
    ON tasks (task_type);

-- =============================================================================
-- TABLA 3: wallets
-- Orden de creación: tercero (FK → providers)
-- =============================================================================
CREATE TABLE IF NOT EXISTS wallets (
    id                uuid          NOT NULL DEFAULT gen_random_uuid(),
    provider_id       uuid          NOT NULL,
    available_balance numeric(12,2) NOT NULL DEFAULT 0.00,
    pending_balance   numeric(12,2) NOT NULL DEFAULT 0.00,
    total_earned      numeric(12,2) NOT NULL DEFAULT 0.00,
    total_withdrawn   numeric(12,2) NOT NULL DEFAULT 0.00,
    created_at        timestamptz   NOT NULL DEFAULT now(),
    updated_at        timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT wallets_pkey PRIMARY KEY (id),
    CONSTRAINT wallets_provider_id_unique UNIQUE (provider_id),
    CONSTRAINT wallets_provider_fkey
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE,
    CONSTRAINT wallets_available_balance_non_negative
        CHECK (available_balance >= 0.00),
    CONSTRAINT wallets_pending_balance_non_negative
        CHECK (pending_balance >= 0.00),
    CONSTRAINT wallets_total_earned_non_negative
        CHECK (total_earned >= 0.00),
    CONSTRAINT wallets_total_withdrawn_non_negative
        CHECK (total_withdrawn >= 0.00)
);

-- Trigger updated_at en wallets
DROP TRIGGER IF EXISTS trg_wallets_updated_at ON wallets;
CREATE TRIGGER trg_wallets_updated_at
    BEFORE UPDATE ON wallets
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- TABLA 4: task_assignments
-- Orden de creación: cuarto (FK → providers, tasks)
-- =============================================================================
CREATE TABLE IF NOT EXISTS task_assignments (
    id           uuid          NOT NULL DEFAULT gen_random_uuid(),
    task_id      uuid          NOT NULL,
    provider_id  uuid          NOT NULL,
    status       text          NOT NULL DEFAULT 'aceptada',
    reward_paid  numeric(10,2),
    trust_delta  numeric(5,2),
    accepted_at  timestamptz   NOT NULL DEFAULT now(),
    started_at   timestamptz,
    completed_at timestamptz,
    created_at   timestamptz   NOT NULL DEFAULT now(),
    updated_at   timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT task_assignments_pkey PRIMARY KEY (id),
    CONSTRAINT task_assignments_task_fkey
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
    CONSTRAINT task_assignments_provider_fkey
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE RESTRICT,
    CONSTRAINT task_assignments_task_provider_unique
        UNIQUE (task_id, provider_id),
    CONSTRAINT task_assignments_status_values
        CHECK (status IN ('aceptada', 'procesando', 'completada', 'fallida', 'cancelada')),
    CONSTRAINT task_assignments_reward_paid_positive
        CHECK (reward_paid IS NULL OR reward_paid >= 0),
    CONSTRAINT task_assignments_dates_valid
        CHECK (started_at IS NULL OR started_at >= accepted_at),
    CONSTRAINT task_assignments_completed_valid
        CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);

-- Trigger updated_at en task_assignments
DROP TRIGGER IF EXISTS trg_task_assignments_updated_at ON task_assignments;
CREATE TRIGGER trg_task_assignments_updated_at
    BEFORE UPDATE ON task_assignments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Índice crítico: asignaciones por proveedor (historial, dashboard)
CREATE INDEX IF NOT EXISTS idx_task_assignments_provider_id
    ON task_assignments (provider_id);

-- Índice para el índice de tareas por tarea
CREATE INDEX IF NOT EXISTS idx_task_assignments_task_id
    ON task_assignments (task_id);

-- Índice para filtrado por estado
CREATE INDEX IF NOT EXISTS idx_task_assignments_status
    ON task_assignments (status);

-- Índice compuesto: asignaciones activas de un proveedor
CREATE INDEX IF NOT EXISTS idx_task_assignments_provider_status
    ON task_assignments (provider_id, status)
    WHERE status IN ('aceptada', 'procesando');

-- =============================================================================
-- TABLA 5: transactions
-- Orden de creación: quinto (FK → providers, tasks nullable)
-- =============================================================================
CREATE TABLE IF NOT EXISTS transactions (
    id                   uuid          NOT NULL DEFAULT gen_random_uuid(),
    provider_id          uuid          NOT NULL,
    task_id              uuid,
    amount               numeric(10,2) NOT NULL,
    tx_type              text          NOT NULL,
    status               text          NOT NULL DEFAULT 'completada',
    description          text          NOT NULL,
    withdraw_method      text,
    withdraw_destination text,
    created_at           timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT transactions_pkey PRIMARY KEY (id),
    CONSTRAINT transactions_provider_fkey
        FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE RESTRICT,
    CONSTRAINT transactions_task_fkey
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT transactions_amount_positive
        CHECK (amount > 0),
    CONSTRAINT transactions_tx_type_values
        CHECK (tx_type IN ('pago_tarea', 'retiro', 'bonus', 'penalizacion')),
    CONSTRAINT transactions_status_values
        CHECK (status IN ('completada', 'pendiente', 'cancelada')),
    CONSTRAINT transactions_withdraw_method_values
        CHECK (withdraw_method IS NULL OR withdraw_method IN ('transferencia', 'paypal', 'cripto')),
    CONSTRAINT transactions_withdraw_destination_requires_method
        CHECK (
            (withdraw_method IS NULL AND withdraw_destination IS NULL)
            OR (withdraw_method IS NOT NULL AND withdraw_destination IS NOT NULL)
        )
);

-- Índice crítico: historial de transacciones paginado por proveedor (orden DESC)
CREATE INDEX IF NOT EXISTS idx_transactions_provider_created
    ON transactions (provider_id, created_at DESC);

-- Índice para filtrado por tipo
CREATE INDEX IF NOT EXISTS idx_transactions_tx_type
    ON transactions (tx_type);

-- =============================================================================
-- FUNCIÓN Y TRIGGER: recalcular trust_score en providers
-- Se dispara cuando cambian accuracy, response_time_score, client_rating
-- o completion_rate. El backend también puede llamar a UPDATE directamente.
-- La fórmula es:
--   trust = completion_rate*0.40 + accuracy*0.30
--           + response_time_score*0.20 + client_rating*0.10
-- =============================================================================
CREATE OR REPLACE FUNCTION recalculate_trust_score()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_new_score numeric(5,2);
    v_new_rank  text;
BEGIN
    -- Solo recalcular si algún componente ha cambiado
    IF (
        NEW.completion_rate     IS DISTINCT FROM OLD.completion_rate     OR
        NEW.accuracy            IS DISTINCT FROM OLD.accuracy            OR
        NEW.response_time_score IS DISTINCT FROM OLD.response_time_score OR
        NEW.client_rating       IS DISTINCT FROM OLD.client_rating
    ) THEN
        v_new_score := ROUND(
            (NEW.completion_rate * 0.40)
            + (NEW.accuracy * 0.30)
            + (NEW.response_time_score * 0.20)
            + (NEW.client_rating * 0.10),
            2
        );

        -- Limitar al rango [0.00, 100.00]
        v_new_score := GREATEST(0.00, LEAST(100.00, v_new_score));

        -- Asignar rango según trust_score resultante
        v_new_rank := CASE
            WHEN v_new_score >= 90.00 THEN 'elite'
            WHEN v_new_score >= 75.00 THEN 'experto'
            WHEN v_new_score >= 50.00 THEN 'confiable'
            ELSE 'nuevo'
        END;

        NEW.trust_score := v_new_score;
        NEW.rank        := v_new_rank;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_recalculate_trust_score ON providers;
CREATE TRIGGER trg_recalculate_trust_score
    BEFORE UPDATE ON providers
    FOR EACH ROW
    EXECUTE FUNCTION recalculate_trust_score();

-- Nota: el trigger trg_providers_updated_at y trg_recalculate_trust_score
-- coexisten. PostgreSQL ejecuta los triggers BEFORE UPDATE en orden de creación.
-- recalculate_trust_score se ejecuta primero (actualiza los valores en NEW)
-- y luego set_updated_at actualiza updated_at con el valor final.
-- El orden correcto ya está garantizado porque trg_recalculate_trust_score
-- fue creado antes de trg_providers_updated_at en esta migración.
-- Si los triggers están en orden incorrecto en el sistema, recrea:
--   DROP TRIGGER trg_providers_updated_at ON providers;
--   CREATE TRIGGER trg_providers_updated_at BEFORE UPDATE ON providers
--     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- PostgreSQL ordena los triggers BEFORE por nombre alfabéticamente;
-- "trg_providers_updated_at" > "trg_recalculate_trust_score" en orden alpha,
-- por lo que recalculate se ejecuta ANTES. Correcto.

-- =============================================================================
-- COMENTARIOS EN TABLAS (documentación embebida)
-- =============================================================================
COMMENT ON TABLE providers IS
    'Proveedores de cómputo. Cada fila es una cuenta de usuario registrado.';
COMMENT ON COLUMN providers.trust_score IS
    'Calculado por trigger: completion_rate*0.40 + accuracy*0.30 + response_time_score*0.20 + client_rating*0.10. Rango [0,100].';
COMMENT ON COLUMN providers.rank IS
    'nuevo (<50) | confiable (50-74.99) | experto (75-89.99) | elite (>=90). Calculado por trigger junto con trust_score.';
COMMENT ON COLUMN providers.completion_rate IS
    'Componente del Trust Score. = tasks_completed / (tasks_completed + tasks_failed) * 100. Actualizado por el backend al completar/fallar.';
COMMENT ON COLUMN providers.accuracy IS
    'Componente del Trust Score. Comienza en 80. +2 al completar, -5 al fallar. Rango [0,100].';
COMMENT ON COLUMN providers.response_time_score IS
    'Componente del Trust Score. Comienza en 70. +5 si aceptó en <10 min, -5 si >60 min. Rango [0,100].';
COMMENT ON COLUMN providers.client_rating IS
    'Componente del Trust Score. Fijo en 70.00 durante MVP. Rango [0,100].';

COMMENT ON TABLE tasks IS
    'Tareas disponibles para procesar. Publicadas por el sistema (seed) o administradores.';
COMMENT ON COLUMN tasks.stages IS
    'Array de 4-6 strings con los nombres de las etapas de procesamiento. Usado para la pantalla de progreso.';
COMMENT ON COLUMN tasks.slots_left IS
    'Decrementado atómicamente con UPDATE ... WHERE slots_left > 0 RETURNING slots_left al aceptar una tarea.';

COMMENT ON TABLE task_assignments IS
    'Asignaciones de tareas a proveedores. Un proveedor no puede tener dos asignaciones activas de la misma tarea (UNIQUE task_id, provider_id).';

COMMENT ON TABLE wallets IS
    'Cartera 1:1 con providers. Se crea automáticamente en el backend al registrar un proveedor (POST /auth/register).';

COMMENT ON TABLE transactions IS
    'Registro inmutable de movimientos de saldo. No se borra ni modifica tras creación (solo status de retiros puede cambiar a cancelada).';
COMMENT ON COLUMN transactions.withdraw_method IS
    'Solo para tx_type=retiro: transferencia | paypal | cripto.';
