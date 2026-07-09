"""
Tests for app.core.rate_limit (docs/04-arquitectura.md §15.1).

Coverage:
- check_rate_limit(): atomic fixed-window increment, 429 once the limit is
  exceeded, Retry-After header, lazy cleanup of stale rows.
- rate_limit_by_ip / rate_limit_by_provider: FastAPI dependency wiring — a
  429 raised inside the dependency is surfaced as an HTTP 429 response by
  the endpoints that use it (POST /auth/register, POST /auth/login,
  POST /work/claim, POST /work/{chunk_id}/submit).

None of these tests hit a real Postgres instance: psycopg2.connect is
replaced with an in-memory fake that reproduces the INSERT ... ON CONFLICT
... RETURNING semantics used by check_rate_limit.
"""
import logging
from contextlib import contextmanager
from unittest.mock import patch

import psycopg2
import pytest
from fastapi import HTTPException

from app.core.rate_limit import check_rate_limit, rate_limit_by_ip, rate_limit_by_provider
from app.core.dependencies import get_current_provider
from app.main import app
from tests.conftest import PROVIDER_ID


# ──────────────────────────────────────────────────────────────────────────────
# In-memory fake for psycopg2.connect, reproducing the UPSERT semantics of
# check_rate_limit's SQL without touching a real database.
# ──────────────────────────────────────────────────────────────────────────────


class _FakeCursor:
    def __init__(self, store: dict, delete_calls: list):
        self._store = store
        self._delete_calls = delete_calls
        self._last_result = None

    def execute(self, sql: str, params=None) -> None:
        normalized = " ".join(sql.split())
        if normalized.startswith("INSERT INTO rate_limit_counters"):
            bucket, window_start = params
            key = (bucket, window_start)
            count = self._store.get(key, 0) + 1
            self._store[key] = count
            self._last_result = (count,)
        elif normalized.startswith("DELETE FROM rate_limit_counters"):
            self._delete_calls.append(True)
            self._last_result = None
        else:
            raise AssertionError(f"Unexpected SQL in fake cursor: {sql!r}")

    def fetchone(self):
        return self._last_result

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakeConnection:
    def __init__(self, store: dict, delete_calls: list):
        self._store = store
        self._delete_calls = delete_calls
        self.committed = False

    def cursor(self):
        return _FakeCursor(self._store, self._delete_calls)

    def commit(self) -> None:
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


@contextmanager
def _fake_psycopg2_connect(store: dict, delete_calls: list):
    """Patch app.core.rate_limit.psycopg2.connect to return a _FakeConnection
    backed by `store` (shared across calls, like a real table would be)."""
    with patch(
        "app.core.rate_limit.psycopg2.connect",
        return_value=_FakeConnection(store, delete_calls),
    ) as mocked:
        yield mocked


# ──────────────────────────────────────────────────────────────────────────────
# check_rate_limit — unit tests
# ──────────────────────────────────────────────────────────────────────────────


def test_check_rate_limit_allows_requests_under_limit():
    """The first `limit` calls for a bucket must not raise."""
    store: dict = {}
    with _fake_psycopg2_connect(store, []):
        for _ in range(5):
            check_rate_limit("test:unit:under-limit", limit=5, window_seconds=60)
    # 5 calls against limit=5 — none of them exceeds it (count > limit only at 6th).


def test_check_rate_limit_raises_429_when_limit_exceeded():
    """The (limit + 1)-th call within the same window must raise HTTPException(429)."""
    store: dict = {}
    bucket = "test:unit:exceeded"
    with _fake_psycopg2_connect(store, []):
        for _ in range(3):
            check_rate_limit(bucket, limit=3, window_seconds=60)

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(bucket, limit=3, window_seconds=60)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "60"


def test_check_rate_limit_retry_after_matches_window_seconds():
    """Retry-After must reflect the window_seconds argument, not a fixed value."""
    store: dict = {}
    bucket = "test:unit:retry-after"
    with _fake_psycopg2_connect(store, []):
        # limit=0 means the very first request already exceeds it (count=1 > 0).
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(bucket, limit=0, window_seconds=3600)

    assert exc_info.value.headers["Retry-After"] == "3600"


def test_check_rate_limit_separate_buckets_do_not_interfere():
    """Different buckets must have independent counters."""
    store: dict = {}
    with _fake_psycopg2_connect(store, []):
        for _ in range(3):
            check_rate_limit("bucket-a", limit=3, window_seconds=60)
        # bucket-b starts fresh even though bucket-a is already at its limit.
        check_rate_limit("bucket-b", limit=3, window_seconds=60)


def test_check_rate_limit_runs_lazy_cleanup_probabilistically():
    """When random.random() falls under _CLEANUP_PROBABILITY, a DELETE runs."""
    store: dict = {}
    delete_calls: list = []
    with _fake_psycopg2_connect(store, delete_calls):
        with patch("app.core.rate_limit.random.random", return_value=0.0):
            check_rate_limit("test:unit:cleanup-triggered", limit=10, window_seconds=60)
    assert delete_calls == [True]


def test_check_rate_limit_skips_cleanup_most_of_the_time():
    store: dict = {}
    delete_calls: list = []
    with _fake_psycopg2_connect(store, delete_calls):
        with patch("app.core.rate_limit.random.random", return_value=0.99):
            check_rate_limit("test:unit:cleanup-skipped", limit=10, window_seconds=60)
    assert delete_calls == []


# ──────────────────────────────────────────────────────────────────────────────
# check_rate_limit — fail-open on psycopg2 failures (EN-MAYOR-02,
# docs/05-review.md 2026-07-09). Before this cycle, /auth/login and
# /auth/register had zero dependency on psycopg2 (REST SDK only); a
# transient pooler failure must not turn into a 500 for either endpoint.
# ──────────────────────────────────────────────────────────────────────────────


def test_check_rate_limit_fails_open_when_connect_raises_psycopg2_error(caplog):
    """A psycopg2.Error while connecting to the pooler must not propagate —
    the request is let through (fail-open) and the failure is logged."""
    with patch(
        "app.core.rate_limit.psycopg2.connect",
        side_effect=psycopg2.OperationalError("could not connect to server"),
    ):
        with caplog.at_level(logging.ERROR):
            check_rate_limit("test:unit:pooler-down-connect", limit=5, window_seconds=60)

    assert any(
        record.levelno == logging.ERROR and "fail-open" in record.message
        for record in caplog.records
    )


def test_check_rate_limit_fails_open_when_execute_raises_psycopg2_error(caplog):
    """A psycopg2.Error raised while executing the UPSERT (not just at connect
    time) must also fail open, not just connection-time failures."""

    class _RaisingCursor:
        def execute(self, *args, **kwargs):
            raise psycopg2.errors.QueryCanceled("statement timeout")

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    class _ConnWithRaisingCursor:
        def cursor(self):
            return _RaisingCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    with patch(
        "app.core.rate_limit.psycopg2.connect",
        return_value=_ConnWithRaisingCursor(),
    ):
        with caplog.at_level(logging.ERROR):
            check_rate_limit("test:unit:pooler-down-execute", limit=5, window_seconds=60)

    assert any(
        record.levelno == logging.ERROR and "fail-open" in record.message
        for record in caplog.records
    )


def test_check_rate_limit_does_not_swallow_non_psycopg2_errors():
    """Only psycopg2.Error should trigger fail-open — a bug elsewhere (e.g. a
    malformed row shape from a compromised fake) must still propagate,
    proving the except clause is specific and not a bare `except Exception`."""
    with patch(
        "app.core.rate_limit.psycopg2.connect",
        side_effect=TypeError("boom - not a psycopg2 error"),
    ):
        with pytest.raises(TypeError):
            check_rate_limit("test:unit:generic-error", limit=5, window_seconds=60)


# ──────────────────────────────────────────────────────────────────────────────
# rate_limit_by_ip / rate_limit_by_provider — dependency wiring
# ──────────────────────────────────────────────────────────────────────────────


def test_rate_limit_by_ip_dependency_calls_check_rate_limit_with_ip_bucket():
    dependency = rate_limit_by_ip("unit-scope", limit=5, window_seconds=60)

    class _FakeClient:
        host = "203.0.113.5"

    class _FakeRequest:
        client = _FakeClient()

    with patch("app.core.rate_limit.check_rate_limit") as mocked:
        dependency(_FakeRequest())

    mocked.assert_called_once_with("unit-scope:ip:203.0.113.5", 5, 60)


def test_rate_limit_by_ip_dependency_handles_missing_client():
    dependency = rate_limit_by_ip("unit-scope", limit=5, window_seconds=60)

    class _FakeRequest:
        client = None

    with patch("app.core.rate_limit.check_rate_limit") as mocked:
        dependency(_FakeRequest())

    mocked.assert_called_once_with("unit-scope:ip:unknown", 5, 60)


def test_rate_limit_by_provider_dependency_calls_check_rate_limit_with_provider_bucket(
    mock_provider: dict,
):
    dependency = rate_limit_by_provider("unit-scope", limit=5, window_seconds=60)

    with patch("app.core.rate_limit.check_rate_limit") as mocked:
        result = dependency(provider=mock_provider)

    mocked.assert_called_once_with(f"unit-scope:provider:{PROVIDER_ID}", 5, 60)
    assert result == mock_provider


# ──────────────────────────────────────────────────────────────────────────────
# End-to-end: a 429 raised by the rate limit dependency reaches the client as
# an HTTP 429, for each of the 4 endpoints named in docs/04-arquitectura.md §15.1.1.
# These tests build their own TestClient (not the shared `client`/
# `unauthenticated_client` fixtures, which bypass rate limiting by default —
# see tests/conftest.py) so the real dependency executes.
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def rate_limited_client(mock_provider: dict):
    """TestClient with authentication overridden but rate-limit dependencies
    left wired to the real `check_rate_limit` (patched per-test below)."""
    from fastapi.testclient import TestClient

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_provider] = lambda: mock_provider
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_register_returns_429_when_rate_limited(rate_limited_client):
    with patch(
        "app.core.rate_limit.check_rate_limit",
        side_effect=HTTPException(
            status_code=429,
            detail="Demasiadas peticiones. Inténtalo de nuevo en unos instantes.",
            headers={"Retry-After": "3600"},
        ),
    ):
        response = rate_limited_client.post(
            "/auth/register",
            json={
                "full_name": "Test Provider",
                "email": "test@example.com",
                "password": "password123",
            },
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "3600"


def test_login_returns_429_when_rate_limited(rate_limited_client):
    with patch(
        "app.core.rate_limit.check_rate_limit",
        side_effect=HTTPException(
            status_code=429,
            detail="Demasiadas peticiones. Inténtalo de nuevo en unos instantes.",
            headers={"Retry-After": "60"},
        ),
    ):
        response = rate_limited_client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_work_claim_returns_429_when_rate_limited(rate_limited_client):
    with patch(
        "app.core.rate_limit.check_rate_limit",
        side_effect=HTTPException(
            status_code=429,
            detail="Demasiadas peticiones. Inténtalo de nuevo en unos instantes.",
            headers={"Retry-After": "60"},
        ),
    ):
        response = rate_limited_client.post("/work/claim", json={"max_chunks": 3})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_work_submit_returns_429_when_rate_limited(rate_limited_client):
    import uuid

    with patch(
        "app.core.rate_limit.check_rate_limit",
        side_effect=HTTPException(
            status_code=429,
            detail="Demasiadas peticiones. Inténtalo de nuevo en unos instantes.",
            headers={"Retry-After": "60"},
        ),
    ):
        response = rate_limited_client.post(
            f"/work/{uuid.uuid4()}/submit",
            json={"result": {"count_sum": 1}, "duration_ms": 10},
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
