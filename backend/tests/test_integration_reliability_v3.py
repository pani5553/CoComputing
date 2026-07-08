"""
Integration tests against the REAL Supabase Postgres DB (SUPABASE_DB_URL),
for the v3 reliability fixes described in docs/04-arquitectura.md §14 plus
the SEC-36 mitigation from docs/06-security.md (2026-07-07 cycle):

  1. TTL de chunks asignados (compute_queries.claim_chunks_atomic)
  2. Transaccionalidad de pago + trust (wallet_queries.credit_reward_and_update_trust)
  3. SEC-36: un proveedor que reclama-y-abandona un chunk (TTL lo devuelve a
     pending sin submit) no puede volver a reclamar ESE MISMO chunk, aunque
     sí puede reclamar cualquier otro (compute_queries.claim_chunks_atomic,
     columna chunks.abandoned_by de migrations/007_chunk_abandon_tracking.sql)

Unlike the rest of the suite (which mocks every DB call — see the header
comments of test_compute.py / test_consensus.py), these two fixes are
precisely about real, multi-statement transactional behavior against
Postgres. A mocked test cannot verify "does the DB actually roll back
correctly / does the TTL predicate actually match rows" — only a real
connection can. This module creates its own throwaway rows (unique UUIDs,
never touching pre-existing data) and cleans them up in `finally`/fixture
teardown, so it is safe to run against the project's real dev/test
Supabase instance.

If SUPABASE_DB_URL is unreachable, every test here is SKIPPED (not failed)
with a clear reason — see `db_conn` fixture.

QA finding (see report to Code Reviewer): as of this writing, the TTL test
below is skipped for a different reason than unreachability — the
`chunks.assigned_at` column does not exist on the configured database,
because migrations/006_chunk_ttl.sql has not been applied there yet. This
was confirmed manually (see `test_ttl_reclaims_expired_assigned_chunk...`
docstring). That is a deployment gap for the Database Engineer
(docs/04-arquitectura.md §14.5), not a code defect — but it means
claim_chunks_atomic() cannot function at all against this database today.
"""
import uuid

import psycopg2
import psycopg2.extras
import pytest

from app.core.config import settings
from app.services import trust_score

pytestmark = pytest.mark.integration


def _count_foreign_active_chunks(cur) -> int:
    """
    Count chunks (across ALL jobs, table-wide) already in 'pending' or
    'assigned' state, BEFORE a test inserts its own throwaway rows.

    claim_chunks_atomic's candidate selection is GLOBAL, not scoped to a
    single job_id (see docs/04-arquitectura.md §14.2.4 — by design, any
    authenticated provider can claim any pending chunk from any job). That
    is safe in production (that is the point of the feature) but means a
    test that calls claim_chunks_atomic for a throwaway, disposable
    provider_id — one that this same test deletes in its teardown — risks
    claiming REAL chunks belonging to real jobs if the database already has
    any in flight, and then, via chunks.assigned_to's ON DELETE SET NULL,
    orphaning them (status stuck at 'assigned' with assigned_to wiped to
    NULL) the moment the throwaway provider row is deleted.

    Used as a safety guard: if this returns > 0, the test using it must
    skip rather than proceed, because it is not safe to exercise
    claim_chunks_atomic's real, unscoped candidate selection against a
    database that already holds real in-flight work.
    """
    cur.execute("SELECT count(*) AS n FROM chunks WHERE status IN ('pending', 'assigned')")
    return cur.fetchone()["n"]


def _insert_bare_provider(cur, provider_id: str) -> None:
    """
    Minimal providers row — id, email, full_name, password_hash are the only
    NOT NULL columns without a default (migrations/001_schema.sql). Used by
    tests in this module that only need a provider row to satisfy FK
    constraints (jobs.client_id, chunks.assigned_to both REFERENCE
    providers(id) — see migrations/004_compute.sql) and don't exercise
    trust/wallet fields.
    """
    cur.execute(
        "INSERT INTO providers (id, email, full_name, password_hash) VALUES (%s, %s, 'QA Integration Test', 'x')",
        (provider_id, f"qa-integration-{provider_id}@test.local"),
    )


# ── Connection plumbing ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_conn():
    """Real psycopg2 connection to SUPABASE_DB_URL. Skips the module if unreachable."""
    try:
        conn = psycopg2.connect(
            settings.supabase_db_url,
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=8,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"No se pudo conectar a SUPABASE_DB_URL: {exc}")
        return
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def chunks_has_assigned_at(db_conn) -> bool:
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'chunks' AND column_name = 'assigned_at'
            """
        )
        return cur.fetchone() is not None


@pytest.fixture(scope="module")
def chunks_has_abandoned_by(db_conn) -> bool:
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'chunks' AND column_name = 'abandoned_by'
            """
        )
        return cur.fetchone() is not None


# ── Problem 1: TTL de chunks asignados ───────────────────────────────────────

def test_ttl_reclaims_expired_assigned_chunk_and_allows_reclaim_by_other_provider(
    db_conn, chunks_has_assigned_at
):
    """
    Recommended integration test from docs/04-arquitectura.md §14.7: create a
    chunk 'assigned' to provider A with assigned_at > CHUNK_ASSIGNMENT_TTL_MINUTES
    in the past, then call claim_chunks_atomic for a DIFFERENT provider B and
    confirm the chunk is (a) freed from A (status back to pending momentarily)
    and (b) immediately re-claimed by B in the same call (per §14.2.4's
    three-sequential-statements design, statement 3 must see statement 1's
    uncommitted changes).
    """
    if not chunks_has_assigned_at:
        pytest.skip(
            "BLOQUEADO — migrations/006_chunk_ttl.sql no se ha aplicado a la "
            "base de datos apuntada por SUPABASE_DB_URL: la columna "
            "chunks.assigned_at no existe (confirmado por "
            "information_schema.columns). Sin esta columna, "
            "claim_chunks_atomic() falla en su primera sentencia con "
            "psycopg2.errors.UndefinedColumn: column \"assigned_at\" does not "
            "exist — no es posible ejercitar el TTL contra esta BD hasta que "
            "el Database Engineer aplique la migración "
            "(docs/04-arquitectura.md §14.5). Este test quedará activo "
            "automáticamente en cuanto la columna exista."
        )

    with db_conn.cursor() as cur:
        foreign_count = _count_foreign_active_chunks(cur)
    if foreign_count > 0:
        pytest.skip(
            f"BLOQUEADO POR SEGURIDAD — la base de datos apuntada por "
            f"SUPABASE_DB_URL ya tiene {foreign_count} chunk(s) en estado "
            "pending/assigned ajenos a este test (jobs reales en curso). "
            "claim_chunks_atomic() selecciona candidatos de forma GLOBAL, no "
            "filtrada por job_id — ejecutar este test aquí reclamaría (y, al "
            "borrar el proveedor de prueba desechable en el teardown, "
            "dejaría huérfanos vía ON DELETE SET NULL) chunks de jobs reales. "
            "Ejecutar este test contra un esquema de test aislado y vacío."
        )

    from app.db.queries import compute_queries

    job_id = str(uuid.uuid4())
    chunk_id = str(uuid.uuid4())
    provider_a = str(uuid.uuid4())  # stale assignee — real provider row (FK), never touched otherwise
    provider_b = str(uuid.uuid4())  # claims it now — also a real provider row (FK)

    with db_conn.cursor() as cur:
        _insert_bare_provider(cur, provider_a)
        _insert_bare_provider(cur, provider_b)
        cur.execute(
            """
            INSERT INTO jobs (id, client_id, job_type, status, params, total_chunks, reward_total)
            VALUES (%s, %s, 'data-processing', 'processing', '{}'::jsonb, 1, 0.10)
            """,
            (job_id, provider_a),
        )
        cur.execute(
            """
            INSERT INTO chunks
                (id, job_id, chunk_index, payload, status, assigned_to, assigned_at, attempts, replicas_needed)
            VALUES
                (%s, %s, 0, '{}'::jsonb, 'assigned', %s, now() - interval '11 minutes', 1, 2)
            """,
            (chunk_id, job_id, provider_a),
        )
    db_conn.commit()

    try:
        claimed, rejected_job_ids = compute_queries.claim_chunks_atomic(provider_b, max_chunks=5)

        claimed_ids = [str(c["chunk_id"]) for c in claimed]
        assert chunk_id in claimed_ids, (
            "El chunk expirado no fue reclamado por el nuevo proveedor — "
            f"claimed={claimed_ids}"
        )

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT status, assigned_to, assigned_at, attempts FROM chunks WHERE id = %s",
                (chunk_id,),
            )
            row = cur.fetchone()

        assert row["status"] == "assigned"
        assert str(row["assigned_to"]) == provider_b
        assert row["assigned_at"] is not None
        # attempts: was 1 (from the stale assignment), TTL reclaim does not
        # touch it, then the claim statement does attempts + 1 => 2.
        assert row["attempts"] == 2
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM chunk_results WHERE chunk_id = %s", (chunk_id,))
            cur.execute("DELETE FROM chunks WHERE id = %s", (chunk_id,))
            cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
            cur.execute("DELETE FROM providers WHERE id IN (%s, %s)", (provider_a, provider_b))
        db_conn.commit()


# ── SEC-36: reclamo-y-abandono repetido del mismo chunk ──────────────────────
#
# docs/06-security.md ("Auditoría — Pagos transaccionales de recompensa...
# 2026-07-07", hallazgo SEC-36): sin esta mitigación, un proveedor podía
# reclamar un chunk, dejarlo expirar sin enviar resultado (TTL lo devuelve a
# pending), y volver a reclamarlo indefinidamente — agotando MAX_CHUNK_ATTEMPTS
# y forzando su rechazo permanente sin ninguna penalización de trust. La
# mitigación (migrations/007_chunk_abandon_tracking.sql, columna
# chunks.abandoned_by) registra, en la propia sentencia 1 de TTL reclaim, qué
# proveedor abandonó cada chunk, y la sentencia 3 (claim) excluye a ese mismo
# proveedor de volver a reclamar ESE chunk en concreto — sí puede reclamar
# cualquier otro chunk pendiente con normalidad.

def test_sec36_provider_who_abandoned_chunk_cannot_reclaim_it_but_can_claim_others(
    db_conn, chunks_has_assigned_at, chunks_has_abandoned_by
):
    if not chunks_has_assigned_at:
        pytest.skip(
            "BLOQUEADO — chunks.assigned_at no existe (migrations/006_chunk_ttl.sql "
            "no aplicada); sin ella claim_chunks_atomic() falla antes de llegar a "
            "ejercitar abandoned_by."
        )
    if not chunks_has_abandoned_by:
        pytest.skip(
            "BLOQUEADO — migrations/007_chunk_abandon_tracking.sql no se ha "
            "aplicado a la base de datos apuntada por SUPABASE_DB_URL: la "
            "columna chunks.abandoned_by no existe (confirmado por "
            "information_schema.columns). La mitigación de SEC-36 no puede "
            "ejercitarse contra esta BD hasta que se aplique la migración."
        )

    with db_conn.cursor() as cur:
        foreign_count = _count_foreign_active_chunks(cur)
    if foreign_count > 0:
        pytest.skip(
            f"BLOQUEADO POR SEGURIDAD — la base de datos apuntada por "
            f"SUPABASE_DB_URL ya tiene {foreign_count} chunk(s) en estado "
            "pending/assigned ajenos a este test (jobs reales en curso). "
            "claim_chunks_atomic() selecciona candidatos de forma GLOBAL, no "
            "filtrada por job_id — ejecutar este test aquí reclamaría (y, al "
            "borrar los proveedores de prueba desechables en el teardown, "
            "dejaría huérfanos vía ON DELETE SET NULL) chunks de jobs reales. "
            "Ejecutar este test contra un esquema de test aislado y vacío."
        )

    from app.db.queries import compute_queries

    job_id = str(uuid.uuid4())
    abandoned_chunk_id = str(uuid.uuid4())
    other_chunk_id = str(uuid.uuid4())
    provider_a = str(uuid.uuid4())  # abandons abandoned_chunk_id — real provider row (FK)
    provider_b = str(uuid.uuid4())  # a different provider, unaffected by A's abandonment

    with db_conn.cursor() as cur:
        _insert_bare_provider(cur, provider_a)
        _insert_bare_provider(cur, provider_b)
        cur.execute(
            """
            INSERT INTO jobs (id, client_id, job_type, status, params, total_chunks, reward_total)
            VALUES (%s, %s, 'data-processing', 'processing', '{}'::jsonb, 2, 0.20)
            """,
            (job_id, provider_a),
        )
        # Chunk A abandoned: still 'assigned' to provider_a, expired past the TTL.
        cur.execute(
            """
            INSERT INTO chunks
                (id, job_id, chunk_index, payload, status, assigned_to, assigned_at, attempts, replicas_needed)
            VALUES
                (%s, %s, 0, '{}'::jsonb, 'assigned', %s, now() - interval '11 minutes', 1, 2)
            """,
            (abandoned_chunk_id, job_id, provider_a),
        )
        # A second, untouched pending chunk on the same job — provider_a must
        # still be able to claim this one normally.
        cur.execute(
            """
            INSERT INTO chunks
                (id, job_id, chunk_index, payload, status, attempts, replicas_needed)
            VALUES
                (%s, %s, 1, '{}'::jsonb, 'pending', 0, 2)
            """,
            (other_chunk_id, job_id),
        )
    db_conn.commit()

    try:
        # Provider A's next claim call triggers the TTL reclaim of its own
        # abandoned chunk (statement 1), which records provider_a in
        # abandoned_by, and then the claim itself (statement 3) must skip
        # abandoned_chunk_id for provider_a while still granting other_chunk_id.
        claimed, _ = compute_queries.claim_chunks_atomic(provider_a, max_chunks=5)
        claimed_ids = [str(c["chunk_id"]) for c in claimed]

        assert abandoned_chunk_id not in claimed_ids, (
            "El proveedor que abandonó el chunk pudo volver a reclamarlo — "
            f"SEC-36 no está mitigado. claimed={claimed_ids}"
        )
        assert other_chunk_id in claimed_ids, (
            "El proveedor no pudo reclamar un chunk DISTINTO al que abandonó — "
            f"la mitigación de SEC-36 es demasiado restrictiva. claimed={claimed_ids}"
        )

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT status, assigned_to, abandoned_by FROM chunks WHERE id = %s",
                (abandoned_chunk_id,),
            )
            abandoned_row = cur.fetchone()

        assert abandoned_row["status"] == "pending", (
            "El chunk abandonado debe quedar en pending (libre para OTRO "
            "proveedor), no reclamado de nuevo por quien lo abandonó."
        )
        assert abandoned_row["assigned_to"] is None
        assert provider_a in [str(p) for p in abandoned_row["abandoned_by"]], (
            "abandoned_by no registró al proveedor que dejó expirar el chunk."
        )

        # A different provider (B) must be able to claim the abandoned chunk
        # with no restriction — the mitigation targets only the abandoning
        # provider, not the chunk itself.
        claimed_b, _ = compute_queries.claim_chunks_atomic(provider_b, max_chunks=5)
        claimed_b_ids = [str(c["chunk_id"]) for c in claimed_b]
        assert abandoned_chunk_id in claimed_b_ids, (
            "Un proveedor DISTINTO al que abandonó el chunk no pudo reclamarlo — "
            f"la mitigación de SEC-36 bloquea a todos, no solo al abandonador. "
            f"claimed_b={claimed_b_ids}"
        )
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chunk_results WHERE chunk_id IN (%s, %s)",
                (abandoned_chunk_id, other_chunk_id),
            )
            cur.execute(
                "DELETE FROM chunks WHERE id IN (%s, %s)",
                (abandoned_chunk_id, other_chunk_id),
            )
            cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
            cur.execute("DELETE FROM providers WHERE id IN (%s, %s)", (provider_a, provider_b))
        db_conn.commit()


# ── Problem 2: transaccionalidad de pago + trust ─────────────────────────────

def _insert_temp_provider(cur, provider_id: str) -> None:
    cur.execute(
        """
        INSERT INTO providers
            (id, email, full_name, password_hash,
             accuracy, completion_rate, response_time_score, client_rating,
             trust_score, rank)
        VALUES
            (%s, %s, 'QA Integration Test', 'x',
             80.00, 70.00, 70.00, 70.00, 73.00, 'confiable')
        """,
        (provider_id, f"qa-integration-{provider_id}@test.local"),
    )
    cur.execute(
        "INSERT INTO wallets (provider_id, available_balance, total_earned) "
        "VALUES (%s, 10.00, 10.00)",
        (provider_id,),
    )


@pytest.fixture
def temp_provider(db_conn):
    """Throwaway provider + wallet row for this test only. Cleaned up after."""
    provider_id = str(uuid.uuid4())
    with db_conn.cursor() as cur:
        _insert_temp_provider(cur, provider_id)
    db_conn.commit()
    yield provider_id
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM transactions WHERE provider_id = %s", (provider_id,))
        cur.execute("DELETE FROM wallets WHERE provider_id = %s", (provider_id,))
        cur.execute("DELETE FROM providers WHERE id = %s", (provider_id,))
    db_conn.commit()


def test_credit_reward_and_update_trust_happy_path_applies_wallet_and_trust(
    db_conn, temp_provider
):
    """Happy path: wallet credited, transaction row inserted, trust fields updated — all three."""
    from app.db.queries import wallet_queries

    expected_accuracy = trust_score.update_accuracy_on_complete(80.00)
    expected_trust = trust_score.calculate_trust_score(
        completion_rate=70.00,
        accuracy=expected_accuracy,
        response_time_score=70.00,
        client_rating=70.00,
    )
    expected_rank = trust_score.get_rank(expected_trust)

    result = wallet_queries.credit_reward_and_update_trust(
        provider_id=temp_provider,
        valid=True,
        reward_amount=0.10,
        description="QA integration test — happy path",
    )

    assert float(result["accuracy"]) == expected_accuracy
    assert float(result["trust_score"]) == expected_trust
    assert result["rank"] == expected_rank

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT available_balance, total_earned FROM wallets WHERE provider_id = %s",
            (temp_provider,),
        )
        wallet = cur.fetchone()
        cur.execute(
            "SELECT count(*) AS n FROM transactions WHERE provider_id = %s",
            (temp_provider,),
        )
        tx_count = cur.fetchone()["n"]

    assert float(wallet["available_balance"]) == 10.10
    assert float(wallet["total_earned"]) == 10.10
    assert tx_count == 1


class _RaisingCursor:
    """Wraps a real psycopg2 cursor; raises on the first execute() whose SQL
    contains `trigger_substring`, otherwise delegates untouched. Used to
    simulate a mid-transaction failure at an exact, chosen point without
    monkeypatching psycopg2's (immutable, C-implemented) cursor type."""

    def __init__(self, real_cursor, trigger_substring: str):
        self._real = real_cursor
        self._trigger = trigger_substring

    def execute(self, query, params=None):
        if isinstance(query, str) and self._trigger in query:
            raise RuntimeError("QA-injected mid-transaction failure")
        return self._real.execute(query, params)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return self._real.__exit__(*exc_info)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _RaisingConn:
    """Wraps a real psycopg2 connection; its .cursor() returns _RaisingCursor."""

    def __init__(self, real_conn, trigger_substring: str):
        self._real = real_conn
        self._trigger = trigger_substring

    def cursor(self, *args, **kwargs):
        return _RaisingCursor(self._real.cursor(*args, **kwargs), self._trigger)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return self._real.__exit__(*exc_info)

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_credit_reward_and_update_trust_is_all_or_nothing_on_mid_transaction_failure(
    db_conn, temp_provider, monkeypatch
):
    """
    The core guarantee this feature exists to provide (docs/04-arquitectura.md
    §14.3): if ANY step fails, NONE of it is applied. We force a failure
    between the wallet credit (already executed, uncommitted) and the final
    providers UPDATE — the exact gap the old two-step code left exposed — and
    confirm the wallet credit that already ran inside the SAME transaction is
    rolled back too, along with the transactions insert.
    """
    from app.db.queries import wallet_queries

    real_connect = wallet_queries.psycopg2.connect

    def patched_connect(*args, **kwargs):
        real_conn = real_connect(*args, **kwargs)
        return _RaisingConn(real_conn, "UPDATE providers")

    monkeypatch.setattr(wallet_queries.psycopg2, "connect", patched_connect)

    with pytest.raises(RuntimeError, match="QA-injected mid-transaction failure"):
        wallet_queries.credit_reward_and_update_trust(
            provider_id=temp_provider,
            valid=True,
            reward_amount=0.10,
            description="QA integration test — forced mid-transaction failure",
        )

    monkeypatch.undo()  # restore real psycopg2.connect before verifying via db_conn

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT available_balance, total_earned FROM wallets WHERE provider_id = %s",
            (temp_provider,),
        )
        wallet = cur.fetchone()
        cur.execute(
            "SELECT count(*) AS n FROM transactions WHERE provider_id = %s",
            (temp_provider,),
        )
        tx_count = cur.fetchone()["n"]
        cur.execute(
            "SELECT accuracy, trust_score, rank FROM providers WHERE id = %s",
            (temp_provider,),
        )
        provider = cur.fetchone()

    # Nothing must have been applied — full rollback, no half-paid state.
    assert float(wallet["available_balance"]) == 10.00, (
        "El crédito de wallet NO se revirtió tras el fallo a mitad de "
        "transacción — esto es exactamente el bug que esta corrección debía "
        "cerrar (proveedor cobrado sin trust actualizado)."
    )
    assert float(wallet["total_earned"]) == 10.00
    assert tx_count == 0, "La fila de transactions quedó insertada pese al rollback."
    assert float(provider["accuracy"]) == 80.00
    assert float(provider["trust_score"]) == 73.00
    assert provider["rank"] == "confiable"
