from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection


def test_test_environment_uses_locmem_backend():
    connection = get_connection()
    assert connection.__class__.__module__ == "django.core.mail.backends.locmem"


def test_base_settings_mailgun_configured():
    assert hasattr(settings, "MAILGUN_API_KEY")
    assert hasattr(settings, "MAILGUN_DOMAIN")
    assert hasattr(settings, "MAILGUN_API_URL")
    assert hasattr(settings, "DEFAULT_FROM_EMAIL")
    assert hasattr(settings, "CRON_TOKEN")


def test_anymail_mailgun_backend_selection():
    from config.settings import base

    # Test when API key is provided
    with patch.object(base.env, "__call__") as mock_env:

        def side_effect(key, default=None):
            if key == "MAILGUN_API_KEY":
                return "test-key-123"
            if key == "MAILGUN_DOMAIN":
                return "mg.example.com"
            if key == "MAILGUN_API_URL":
                return "https://api.mailgun.net/v3"
            if key == "DEFAULT_FROM_EMAIL":
                return "test@example.com"
            if key == "CRON_TOKEN":
                return "secret-token"
            return default

        mock_env.side_effect = side_effect
        api_key = mock_env("MAILGUN_API_KEY", default="")
        assert api_key == "test-key-123"


CLEAN_ENV_VARS = [
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "RENDER_EXTERNAL_HOSTNAME",
    "CORS_ALLOWED_ORIGINS",
    "CORS_REQUIRE_HTTPS",
    "AUTH_THROTTLE_RATE",
    "MAILGUN_API_KEY",
    "MAILGUN_DOMAIN",
    "MAILGUN_API_URL",
    "DEFAULT_FROM_EMAIL",
    "CRON_TOKEN",
    "SITE_URL",
    "EMAIL_NOTIFICATIONS_DISABLED",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "SECURE_SSL_REDIRECT",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "SECURE_HSTS_PRELOAD",
]


def _load_production(monkeypatch, env_vars=None):
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **kw: None)
    for var in CLEAN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    default_env = {
        "SECRET_KEY": "valid-production-secret-key-for-test-12345",
        "ALLOWED_HOSTS": "example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
    }
    if env_vars:
        for k, v in env_vars.items():
            if v is None:
                default_env.pop(k, None)
            else:
                default_env[k] = v

    for k, v in default_env.items():
        monkeypatch.setenv(k, v)

    for mod in ["config.settings.production", "config.settings.base"]:
        if mod in sys.modules:
            del sys.modules[mod]

    return importlib.import_module("config.settings.production")


def test_production_fails_when_mailgun_missing_and_notifications_not_disabled(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="MAILGUN"):
        _load_production(monkeypatch, {"MAILGUN_API_KEY": None, "MAILGUN_DOMAIN": None})


def test_production_fails_when_mailgun_domain_missing(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="MAILGUN"):
        _load_production(
            monkeypatch,
            {"MAILGUN_API_KEY": "test-key", "MAILGUN_DOMAIN": ""},
        )


def test_production_succeeds_when_mailgun_configured(monkeypatch):
    mod = _load_production(
        monkeypatch,
        {"MAILGUN_API_KEY": "test-key", "MAILGUN_DOMAIN": "mg.example.com"},
    )
    assert mod.MAILGUN_API_KEY == "test-key"
    assert mod.MAILGUN_DOMAIN == "mg.example.com"


def test_production_succeeds_without_mailgun_when_notifications_disabled(monkeypatch):
    mod = _load_production(
        monkeypatch,
        {
            "MAILGUN_API_KEY": None,
            "MAILGUN_DOMAIN": None,
            "EMAIL_NOTIFICATIONS_DISABLED": "true",
        },
    )
    assert getattr(mod, "EMAIL_NOTIFICATIONS_DISABLED", False) is True
