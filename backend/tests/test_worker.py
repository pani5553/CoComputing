"""
Tests for the worker's process isolation (app/worker/sandbox.py) and
environment-based credentials (app/worker/main.py) — docs/04-arquitectura.md
§15.2 and §15.3.

There were previously no unit tests for app/worker/ (confirmed by
docs/04-estructura.md); this file adds the coverage recommended explicitly
in §15.8 of that document: resolve_worker_credentials() precedence and
run_chunk_sandboxed() timeout handling.
"""
import argparse
import logging
import os

import pytest

from app.worker import sandbox
from app.worker.main import resolve_worker_credentials


# ──────────────────────────────────────────────────────────────────────────────
# resolve_worker_credentials — env vars vs. deprecated CLI args
# ──────────────────────────────────────────────────────────────────────────────


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    return parser


def test_env_vars_used_when_no_cli_args(monkeypatch):
    monkeypatch.setenv("CC_WORKER_EMAIL", "env-worker@example.com")
    monkeypatch.setenv("CC_WORKER_PASSWORD", "env-secret-pw")
    parser = _make_parser()
    args = parser.parse_args([])

    email, password = resolve_worker_credentials(args, parser)

    assert email == "env-worker@example.com"
    assert password == "env-secret-pw"


def test_cli_args_used_as_fallback_when_no_env_vars(monkeypatch, caplog):
    monkeypatch.delenv("CC_WORKER_EMAIL", raising=False)
    monkeypatch.delenv("CC_WORKER_PASSWORD", raising=False)
    parser = _make_parser()
    args = parser.parse_args(["--email", "cli-worker@example.com", "--password", "cli-secret-pw"])

    with caplog.at_level(logging.WARNING):
        email, password = resolve_worker_credentials(args, parser)

    assert email == "cli-worker@example.com"
    assert password == "cli-secret-pw"
    assert any("DEPRECADO" in record.message for record in caplog.records)


def test_env_var_password_takes_precedence_over_cli_arg(monkeypatch, caplog):
    """
    Precedence: env var wins if both are present — an accidental stale value
    in --password should never silently override the environment's config
    (docs/04-arquitectura.md §15.2.1).
    """
    monkeypatch.setenv("CC_WORKER_EMAIL", "env-worker@example.com")
    monkeypatch.setenv("CC_WORKER_PASSWORD", "env-secret-pw")
    parser = _make_parser()
    args = parser.parse_args(
        ["--email", "cli-worker@example.com", "--password", "cli-secret-pw"]
    )

    with caplog.at_level(logging.WARNING):
        email, password = resolve_worker_credentials(args, parser)

    assert email == "env-worker@example.com"
    assert password == "env-secret-pw"
    # --password was passed but CC_WORKER_PASSWORD also was: no deprecation warning
    # should fire for the password (env var already wins), unlike the CLI-only case.
    assert not any(
        "DEPRECADO: --password" in record.message for record in caplog.records
    )


def test_missing_credentials_raises_system_exit(monkeypatch):
    monkeypatch.delenv("CC_WORKER_EMAIL", raising=False)
    monkeypatch.delenv("CC_WORKER_PASSWORD", raising=False)
    parser = _make_parser()
    args = parser.parse_args([])

    with pytest.raises(SystemExit):
        resolve_worker_credentials(args, parser)


# ──────────────────────────────────────────────────────────────────────────────
# run_chunk_sandboxed — process isolation
# ──────────────────────────────────────────────────────────────────────────────


def test_run_chunk_sandboxed_success():
    """A well-formed data-processing chunk completes normally inside the sandbox."""
    payload = {
        "rows": [[1], [2], [3]],
        "columns": ["value"],
        "operation": "sum",
        "target_columns": ["value"],
    }

    result, duration_ms = sandbox.run_chunk_sandboxed("data-processing", payload)

    assert result == {"value_sum": 6.0}
    assert duration_ms >= 1


def test_run_chunk_sandboxed_unsupported_job_type():
    result, duration_ms = sandbox.run_chunk_sandboxed("no-such-job-type", {})

    assert "error" in result
    assert "unsupported job_type" in result["error"]
    assert duration_ms >= 1


def test_run_chunk_sandboxed_aborts_cleanly_on_timeout(monkeypatch):
    """
    A chunk that doesn't finish within the timeout budget must be aborted
    cleanly: run_chunk_sandboxed returns an error dict (no exception
    propagates, the calling worker process is never affected) and the
    subprocess is no longer alive afterwards.

    Reducing CHUNK_TIMEOUT_SECONDS to (effectively) zero makes this
    deterministic without needing a plugin that actually hangs: even the
    fastest possible child process (spawn + import + dispatch) takes longer
    than a ~0s budget, so proc.join(timeout=...) reliably returns while the
    child is still starting up, exercising the exact same terminate/kill
    path that a genuinely hung chunk would hit.
    """
    monkeypatch.setattr(sandbox, "CHUNK_TIMEOUT_SECONDS", 0)

    payload = {
        "rows": [[1], [2], [3]],
        "columns": ["value"],
        "operation": "sum",
        "target_columns": ["value"],
    }
    result, duration_ms = sandbox.run_chunk_sandboxed("data-processing", payload)

    assert "error" in result
    assert "timed out" in result["error"]
    assert duration_ms >= 1


def test_run_chunk_sandboxed_returns_tuple_shape():
    """Return type must always be (dict, int) regardless of outcome, matching
    the signature process_chunk() in app/worker/main.py delegates to."""
    result, duration_ms = sandbox.run_chunk_sandboxed("data-processing", {})

    assert isinstance(result, dict)
    assert isinstance(duration_ms, int)


# ──────────────────────────────────────────────────────────────────────────────
# _scrub_child_environment / _child_entrypoint — env isolation (SEC-37,
# docs/06-security.md 2026-07-09). The sandboxed subprocess previously
# inherited the full parent environment, including CC_WORKER_EMAIL/
# CC_WORKER_PASSWORD, which plugin.process() never needs (auth already
# happened before any chunk exists). These tests run against the real
# os.environ of the test process (there's no other way to observe what a
# freshly-spawned child would see without spawning one), so each test saves
# and restores the full environment in a finally block to avoid leaking
# mutations into the rest of the suite.
# ──────────────────────────────────────────────────────────────────────────────


def test_scrub_child_environment_removes_non_allowlisted_vars():
    saved = dict(os.environ)
    try:
        os.environ["CC_WORKER_PASSWORD"] = "super-secret"
        os.environ["CC_WORKER_EMAIL"] = "worker@example.com"
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "srv-key"

        sandbox._scrub_child_environment()

        assert "CC_WORKER_PASSWORD" not in os.environ
        assert "CC_WORKER_EMAIL" not in os.environ
        assert "SUPABASE_SERVICE_ROLE_KEY" not in os.environ
    finally:
        os.environ.clear()
        os.environ.update(saved)


def test_scrub_child_environment_keeps_allowlisted_vars():
    saved = dict(os.environ)
    try:
        os.environ["PATH"] = saved.get("PATH", "/usr/bin")

        sandbox._scrub_child_environment()

        assert "PATH" in os.environ
    finally:
        os.environ.clear()
        os.environ.update(saved)


def test_child_entrypoint_scrubs_environment_before_running_plugin():
    """_child_entrypoint must scrub the environment as its very first action —
    by the time plugin.process() (or, here, the unsupported-job-type branch)
    runs, CC_WORKER_PASSWORD/CC_WORKER_EMAIL must already be gone from
    os.environ, proving a compromised plugin can't read them directly."""
    saved = dict(os.environ)
    captured_env: dict = {}

    class _FakeQueue:
        def put(self, item):
            captured_env.update(os.environ)

    try:
        os.environ["CC_WORKER_PASSWORD"] = "super-secret"
        os.environ["CC_WORKER_EMAIL"] = "worker@example.com"

        sandbox._child_entrypoint("no-such-job-type", {}, _FakeQueue())
    finally:
        os.environ.clear()
        os.environ.update(saved)

    assert "CC_WORKER_PASSWORD" not in captured_env
    assert "CC_WORKER_EMAIL" not in captured_env
