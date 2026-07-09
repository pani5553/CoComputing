"""
Tests for app.core.config.Settings / get_settings (EN-MAYOR-01,
docs/05-review.md 2026-07-09).

`extra="ignore"` silently dropped any unrecognized key with zero
visibility anywhere — a typo in a field that has a default (in particular
ENVIRONMENT, e.g. "ENVIRONEMNT=production") would silently keep that field
at its default ("development") with no signal in logs. `extra="allow"`
keeps the same non-fatal behavior (no ValidationError, so a genuinely
obsolete variable like CORS_ORIGINS doesn't break config loading — see
EN-INFO-01) while making the extra keys inspectable via `model_extra`;
`get_settings()` logs them as a warning at startup.

Note on scope: pydantic-settings' EnvSettingsSource (plain OS environment
variables, as opposed to a parsed `.env` file) only ever looks up the
specific env var names backing declared fields — confirmed empirically
that it never surfaces an unrecognized *OS* env var via `model_extra`,
regardless of `extra="forbid"/"allow"/"ignore"`. Only unrecognized keys
coming from the parsed `.env` file (or from explicit init kwargs) show up
in `model_extra`. These tests exercise that real, supported path — the
same one that made `CORS_ORIGINS` visible in the Reviewer's reproduction.
"""
import logging

from app.core import config as config_module
from app.core.config import Settings

_REQUIRED = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
    "SUPABASE_DB_URL": "postgresql://user:pass@localhost:5432/db",
    "JWT_SECRET_KEY": "test-secret",
}


def _write_env_file(tmp_path, extra_lines: str = "") -> str:
    lines = [f"{k}={v}" for k, v in _REQUIRED.items()]
    content = "\n".join(lines) + "\n" + extra_lines
    path = tmp_path / "test.env"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_settings_does_not_raise_on_unrecognized_env_file_key(tmp_path):
    """extra='allow' must not raise ValidationError for an unrecognized key in
    the .env file — unlike the pydantic-settings default (extra='forbid'),
    which would hard-fail config loading over an obsolete variable like
    CORS_ORIGINS (EN-INFO-01)."""
    env_path = _write_env_file(tmp_path, "CORS_ORIGINS=http://localhost:5173\n")

    settings = Settings(_env_file=env_path)

    assert settings.model_extra.get("cors_origins") == "http://localhost:5173"


def test_settings_surfaces_typo_of_default_backed_field_as_extra(tmp_path):
    """A typo of a field that has a default (ENVIRONMENT, in particular) must
    not silently keep the default with zero trace — it must show up in
    model_extra so get_settings() can warn about it."""
    env_path = _write_env_file(tmp_path, "ENVIRONEMNT=production\n")

    settings = Settings(_env_file=env_path)

    # The typo'd key never binds to the real `environment` field: the field
    # silently keeps its default...
    assert settings.environment == "development"
    assert settings.is_production is False
    # ...but it must be visible as an extra so it isn't a silent no-op.
    assert settings.model_extra.get("environemnt") == "production"


def test_settings_has_no_extras_when_env_file_only_has_known_keys(tmp_path):
    env_path = _write_env_file(tmp_path)

    settings = Settings(_env_file=env_path)

    assert settings.model_extra == {}


def test_get_settings_logs_warning_listing_extra_keys(monkeypatch, caplog):
    """get_settings() must log a startup warning naming every extra key found,
    so a typo'd or obsolete variable is visible in deploy logs without
    turning config loading into a hard failure."""

    class _FakeSettingsInstance:
        model_extra = {"cors_origins": "http://localhost:5173", "environemnt": "production"}

    monkeypatch.setattr(config_module, "Settings", lambda: _FakeSettingsInstance())

    with caplog.at_level(logging.WARNING):
        result = config_module.get_settings.__wrapped__()

    assert result is not None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "cors_origins" in warnings[0].message
    assert "environemnt" in warnings[0].message


def test_get_settings_does_not_log_when_no_extra_keys(monkeypatch, caplog):
    class _FakeSettingsInstance:
        model_extra: dict = {}

    monkeypatch.setattr(config_module, "Settings", lambda: _FakeSettingsInstance())

    with caplog.at_level(logging.WARNING):
        config_module.get_settings.__wrapped__()

    assert not any(r.levelno == logging.WARNING for r in caplog.records)


def test_get_settings_handles_none_model_extra(monkeypatch, caplog):
    """model_extra can be None (no extras at all) rather than an empty dict —
    get_settings() must not crash on that shape."""

    class _FakeSettingsInstance:
        model_extra = None

    monkeypatch.setattr(config_module, "Settings", lambda: _FakeSettingsInstance())

    with caplog.at_level(logging.WARNING):
        config_module.get_settings.__wrapped__()

    assert not any(r.levelno == logging.WARNING for r in caplog.records)
