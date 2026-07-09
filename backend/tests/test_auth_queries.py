"""
Tests for app.db.queries.auth_queries — defense-in-depth email
normalization (EN-CRIT-01, docs/05-review.md 2026-07-09).

`get_provider_by_email` must lowercase the email itself, not rely solely on
the Pydantic validators upstream (LoginRequest.email_normalize /
RegisterRequest.email_format_strict) — a future caller that bypasses that
validation layer (a script, another service, a direct call into this
module) must still get a case-insensitive lookup against `providers.email`,
a plain `text` column with a case-sensitive UNIQUE constraint (no `citext`,
no `lower()` index).
"""
from unittest.mock import MagicMock

from app.db.queries import auth_queries


def _fake_supabase_returning(rows: list[dict]) -> MagicMock:
    """Build a MagicMock reproducing the
    .table().select().eq().limit().execute() chain used by
    get_provider_by_email, with `response.data` set to `rows`."""
    fake_client = MagicMock()
    execute_result = MagicMock()
    execute_result.data = rows
    (
        fake_client.table.return_value.select.return_value.eq.return_value
        .limit.return_value.execute.return_value
    ) = execute_result
    return fake_client


def test_get_provider_by_email_lowercases_mixed_case_input(monkeypatch):
    fake_client = _fake_supabase_returning([{"id": "p1", "email": "ana@example.com"}])
    monkeypatch.setattr(auth_queries, "get_supabase", lambda: fake_client)

    result = auth_queries.get_provider_by_email("Ana@Example.com")

    assert result == {"id": "p1", "email": "ana@example.com"}
    eq_mock = fake_client.table.return_value.select.return_value.eq
    eq_mock.assert_called_once_with("email", "ana@example.com")


def test_get_provider_by_email_lowercases_fully_uppercase_input(monkeypatch):
    fake_client = _fake_supabase_returning([])
    monkeypatch.setattr(auth_queries, "get_supabase", lambda: fake_client)

    auth_queries.get_provider_by_email("SOMEONE@EXAMPLE.COM")

    eq_mock = fake_client.table.return_value.select.return_value.eq
    eq_mock.assert_called_once_with("email", "someone@example.com")


def test_get_provider_by_email_passes_through_already_lowercase_input(monkeypatch):
    fake_client = _fake_supabase_returning([{"id": "p1", "email": "ana@example.com"}])
    monkeypatch.setattr(auth_queries, "get_supabase", lambda: fake_client)

    auth_queries.get_provider_by_email("ana@example.com")

    eq_mock = fake_client.table.return_value.select.return_value.eq
    eq_mock.assert_called_once_with("email", "ana@example.com")


def test_get_provider_by_email_returns_none_when_not_found(monkeypatch):
    fake_client = _fake_supabase_returning([])
    monkeypatch.setattr(auth_queries, "get_supabase", lambda: fake_client)

    result = auth_queries.get_provider_by_email("nobody@example.com")

    assert result is None
