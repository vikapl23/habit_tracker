import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

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


def load_production_settings(monkeypatch, env_vars=None):
    """Helper to reload production settings cleanly with specific env vars."""
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **kw: None)
    for var in CLEAN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    default_env = {
        "SECRET_KEY": "valid-production-secret-key-for-test-12345",
        "ALLOWED_HOSTS": "example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
        "EMAIL_NOTIFICATIONS_DISABLED": "true",
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


def test_production_fails_without_secret_key(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        load_production_settings(monkeypatch, {"SECRET_KEY": None})


def test_production_fails_with_insecure_default_secret_key(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        load_production_settings(
            monkeypatch,
            {
                "SECRET_KEY": "django-insecure-development-secret-key-change-in-production-12345",
            },
        )


def test_production_fails_without_allowed_hosts(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(
            monkeypatch,
            {
                "ALLOWED_HOSTS": None,
            },
        )


def test_production_fails_with_wildcard_allowed_hosts(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(
            monkeypatch,
            {
                "SECRET_KEY": "valid-production-secret-key-for-test-12345",
                "ALLOWED_HOSTS": "*",
            },
        )


def test_production_fails_with_wildcard_in_allowed_hosts_list(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(
            monkeypatch,
            {
                "SECRET_KEY": "valid-production-secret-key-for-test-12345",
                "ALLOWED_HOSTS": "example.com,*",
            },
        )


def test_production_fails_with_empty_allowed_hosts(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(
            monkeypatch,
            {
                "SECRET_KEY": "valid-production-secret-key-for-test-12345",
                "ALLOWED_HOSTS": "",
            },
        )


def test_production_fails_without_cors_allowed_origins(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="CORS_ALLOWED_ORIGINS"):
        load_production_settings(monkeypatch, {"CORS_ALLOWED_ORIGINS": None})


def test_production_fails_with_wildcard_cors_allowed_origins(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="CORS_ALLOWED_ORIGINS"):
        load_production_settings(monkeypatch, {"CORS_ALLOWED_ORIGINS": "*"})


def test_production_fails_with_insecure_http_cors_allowed_origins(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="https://"):
        load_production_settings(monkeypatch, {"CORS_ALLOWED_ORIGINS": "http://app.example.com"})


def test_production_succeeds_with_valid_env(monkeypatch):
    settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com,api.example.com",
            "CORS_ALLOWED_ORIGINS": "https://app.example.com,https://dashboard.example.com",
        },
    )
    assert settings.DEBUG is False
    assert settings.ALLOWED_HOSTS == ["example.com", "api.example.com"]
    assert settings.CORS_ALLOWED_ORIGINS == [
        "https://app.example.com",
        "https://dashboard.example.com",
    ]
    assert settings.SECRET_KEY == "valid-production-secret-key-for-test-12345"


def test_production_automatically_adds_render_external_hostname(monkeypatch):
    settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com",
            "RENDER_EXTERNAL_HOSTNAME": "habit-tracker-backend.onrender.com",
        },
    )
    assert settings.ALLOWED_HOSTS == ["example.com", "habit-tracker-backend.onrender.com"]


def test_production_does_not_duplicate_render_external_hostname(monkeypatch):
    settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com,habit-tracker-backend.onrender.com",
            "RENDER_EXTERNAL_HOSTNAME": "habit-tracker-backend.onrender.com",
        },
    )
    assert settings.ALLOWED_HOSTS == ["example.com", "habit-tracker-backend.onrender.com"]


def test_base_settings_fails_when_secret_key_is_missing(monkeypatch):
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **kw: None)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    for mod in ["config.settings.base"]:
        if mod in sys.modules:
            del sys.modules[mod]
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        importlib.import_module("config.settings.base")


def test_base_settings_fails_when_secret_key_is_empty(monkeypatch):
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **kw: None)
    monkeypatch.setenv("SECRET_KEY", "")
    for mod in ["config.settings.base"]:
        if mod in sys.modules:
            del sys.modules[mod]
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        importlib.import_module("config.settings.base")


def test_base_settings_allowed_hosts_default(monkeypatch):
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **kw: None)
    monkeypatch.setenv("SECRET_KEY", "dummy-secret-key-for-test")
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    for mod in ["config.settings.base"]:
        if mod in sys.modules:
            del sys.modules[mod]
    base = importlib.import_module("config.settings.base")
    assert base.ALLOWED_HOSTS == []


def test_local_settings_allowed_hosts_default(monkeypatch):
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **kw: None)
    monkeypatch.setenv("SECRET_KEY", "dummy-secret-key-for-test")
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    for mod in ["config.settings.local", "config.settings.base"]:
        if mod in sys.modules:
            del sys.modules[mod]
    local = importlib.import_module("config.settings.local")
    assert set(local.ALLOWED_HOSTS) == {"localhost", "127.0.0.1"}


def test_env_example_contains_placeholder_and_no_wildcard_hosts():
    from pathlib import Path

    env_example = Path(__file__).resolve().parent.parent.parent.parent / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    assert "django-insecure-development-secret-key-change-in-production-12345" not in content
    assert "ALLOWED_HOSTS=*" not in content
    assert "SECRET_KEY=" in content
    assert "ALLOWED_HOSTS=" in content


def test_test_settings_uses_md5_password_hasher():
    test_settings = importlib.import_module("config.settings.test")
    assert hasattr(test_settings, "PASSWORD_HASHERS")
    assert test_settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.MD5PasswordHasher"


def test_local_settings_does_not_use_md5_hasher():
    local_settings = importlib.import_module("config.settings.local")
    hashers = getattr(local_settings, "PASSWORD_HASHERS", None)
    if hashers:
        assert "django.contrib.auth.hashers.MD5PasswordHasher" not in hashers


def test_production_settings_does_not_use_md5_hasher(monkeypatch):
    prod_settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com",
        },
    )
    hashers = getattr(prod_settings, "PASSWORD_HASHERS", None)
    if hashers:
        assert "django.contrib.auth.hashers.MD5PasswordHasher" not in hashers


def load_local_settings(monkeypatch, env_vars=None):
    """Helper to reload local settings cleanly with specific env vars."""
    monkeypatch.setattr("environ.Env.read_env", lambda *a, **kw: None)
    monkeypatch.delenv("AUTH_THROTTLE_RATE", raising=False)

    if env_vars:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)

    for mod in ["config.settings.local", "config.settings.base"]:
        if mod in sys.modules:
            del sys.modules[mod]

    return importlib.import_module("config.settings.local")


def test_production_auth_throttle_rate_default(monkeypatch):
    prod_settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com",
        },
    )
    assert prod_settings.AUTH_THROTTLE_RATE == "5/minute"
    assert prod_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"] == "5/minute"


def test_production_auth_throttle_rate_custom(monkeypatch):
    prod_settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com",
            "AUTH_THROTTLE_RATE": "20/minute",
        },
    )
    assert prod_settings.AUTH_THROTTLE_RATE == "20/minute"
    assert prod_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"] == "20/minute"


def test_local_auth_throttle_rate_default(monkeypatch):
    local_settings = load_local_settings(monkeypatch)
    assert local_settings.AUTH_THROTTLE_RATE == "100/minute"
    assert local_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"] == "100/minute"


def test_local_auth_throttle_rate_custom(monkeypatch):
    local_settings = load_local_settings(
        monkeypatch,
        {
            "AUTH_THROTTLE_RATE": "250/minute",
        },
    )
    assert local_settings.AUTH_THROTTLE_RATE == "250/minute"
    assert local_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"] == "250/minute"


def test_test_auth_throttle_rate_disabled_in_test_settings():
    test_settings = importlib.import_module("config.settings.test")
    assert getattr(test_settings, "AUTH_THROTTLE_RATE", None) is None
    assert test_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"] is None


def test_simple_jwt_settings_rotation_and_blacklist_enabled():
    base_settings = importlib.import_module("config.settings.base")
    assert "rest_framework_simplejwt.token_blacklist" in base_settings.INSTALLED_APPS
    assert base_settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS") is True
    assert base_settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION") is True


def test_storages_configured_in_base_settings():
    base_settings = importlib.import_module("config.settings.base")
    assert hasattr(base_settings, "STORAGES")
    assert "default" in base_settings.STORAGES
    assert "staticfiles" in base_settings.STORAGES
    assert (
        base_settings.STORAGES["staticfiles"]["BACKEND"]
        == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )
    assert not hasattr(base_settings, "STATICFILES_STORAGE")


def test_production_uses_storages_instead_of_staticfiles_storage(monkeypatch):
    prod_settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com",
        },
    )
    assert hasattr(prod_settings, "STORAGES")
    assert (
        prod_settings.STORAGES["staticfiles"]["BACKEND"]
        == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )
    assert "default" in prod_settings.STORAGES
    assert not hasattr(prod_settings, "STATICFILES_STORAGE")


def test_production_configurable_security_settings_defaults(monkeypatch):
    prod_settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com",
        },
    )
    assert prod_settings.SECURE_SSL_REDIRECT is True
    assert prod_settings.SESSION_COOKIE_SECURE is True
    assert prod_settings.CSRF_COOKIE_SECURE is True
    assert prod_settings.SECURE_HSTS_SECONDS == 31536000
    assert prod_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert prod_settings.SECURE_HSTS_PRELOAD is True
    assert prod_settings.CORS_REQUIRE_HTTPS is True


def test_production_configurable_security_settings_relaxation(monkeypatch):
    prod_settings = load_production_settings(
        monkeypatch,
        {
            "SECRET_KEY": "valid-production-secret-key-for-test-12345",
            "ALLOWED_HOSTS": "example.com",
            "CORS_ALLOWED_ORIGINS": "http://localhost:3000",
            "CORS_REQUIRE_HTTPS": "False",
            "SECURE_SSL_REDIRECT": "False",
            "SESSION_COOKIE_SECURE": "False",
            "CSRF_COOKIE_SECURE": "False",
            "SECURE_HSTS_SECONDS": "0",
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": "False",
            "SECURE_HSTS_PRELOAD": "False",
        },
    )
    assert prod_settings.SECURE_SSL_REDIRECT is False
    assert prod_settings.SESSION_COOKIE_SECURE is False
    assert prod_settings.CSRF_COOKIE_SECURE is False
    assert prod_settings.SECURE_HSTS_SECONDS == 0
    assert prod_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is False
    assert prod_settings.SECURE_HSTS_PRELOAD is False
    assert prod_settings.CORS_REQUIRE_HTTPS is False
    assert prod_settings.CORS_ALLOWED_ORIGINS == ["http://localhost:3000"]


def test_production_fails_without_mailgun_when_notifications_not_disabled(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="MAILGUN"):
        load_production_settings(
            monkeypatch,
            {
                "EMAIL_NOTIFICATIONS_DISABLED": None,
                "MAILGUN_API_KEY": None,
                "MAILGUN_DOMAIN": None,
            },
        )


def test_production_succeeds_when_email_notifications_disabled(monkeypatch):
    prod_settings = load_production_settings(
        monkeypatch,
        {
            "EMAIL_NOTIFICATIONS_DISABLED": "true",
            "MAILGUN_API_KEY": None,
            "MAILGUN_DOMAIN": None,
        },
    )
    assert prod_settings.EMAIL_NOTIFICATIONS_DISABLED is True
