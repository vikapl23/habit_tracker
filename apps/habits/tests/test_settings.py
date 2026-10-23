import importlib
import sys
import pytest
from django.core.exceptions import ImproperlyConfigured


def load_production_settings(monkeypatch, env_vars=None):
    """Helper to reload production settings cleanly with specific env vars."""
    monkeypatch.setattr('environ.Env.read_env', lambda *a, **kw: None)
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('ALLOWED_HOSTS', raising=False)
    monkeypatch.delenv('AUTH_THROTTLE_RATE', raising=False)

    if env_vars:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)

    for mod in ['config.settings.production', 'config.settings.base']:
        if mod in sys.modules:
            del sys.modules[mod]

    return importlib.import_module('config.settings.production')


def test_production_fails_without_secret_key(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        load_production_settings(monkeypatch, {'ALLOWED_HOSTS': 'example.com'})


def test_production_fails_with_insecure_default_secret_key(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        load_production_settings(monkeypatch, {
            'SECRET_KEY': 'django-insecure-development-secret-key-change-in-production-12345',
            'ALLOWED_HOSTS': 'example.com',
        })


def test_production_fails_without_allowed_hosts(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(monkeypatch, {
            'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
        })


def test_production_fails_with_wildcard_allowed_hosts(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(monkeypatch, {
            'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
            'ALLOWED_HOSTS': '*',
        })


def test_production_fails_with_wildcard_in_allowed_hosts_list(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(monkeypatch, {
            'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
            'ALLOWED_HOSTS': 'example.com,*',
        })


def test_production_fails_with_empty_allowed_hosts(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        load_production_settings(monkeypatch, {
            'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
            'ALLOWED_HOSTS': '',
        })


def test_production_succeeds_with_valid_env(monkeypatch):
    settings = load_production_settings(monkeypatch, {
        'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
        'ALLOWED_HOSTS': 'example.com,api.example.com',
    })
    assert settings.DEBUG is False
    assert settings.ALLOWED_HOSTS == ['example.com', 'api.example.com']
    assert settings.SECRET_KEY == 'valid-production-secret-key-for-test-12345'


def test_base_settings_allowed_hosts_default(monkeypatch):
    monkeypatch.setattr('environ.Env.read_env', lambda *a, **kw: None)
    monkeypatch.delenv('ALLOWED_HOSTS', raising=False)
    for mod in ['config.settings.base']:
        if mod in sys.modules:
            del sys.modules[mod]
    base = importlib.import_module('config.settings.base')
    assert base.ALLOWED_HOSTS == ['*']


def test_test_settings_uses_md5_password_hasher():
    test_settings = importlib.import_module('config.settings.test')
    assert hasattr(test_settings, 'PASSWORD_HASHERS')
    assert test_settings.PASSWORD_HASHERS[0] == 'django.contrib.auth.hashers.MD5PasswordHasher'


def test_local_settings_does_not_use_md5_hasher():
    local_settings = importlib.import_module('config.settings.local')
    hashers = getattr(local_settings, 'PASSWORD_HASHERS', None)
    if hashers:
        assert 'django.contrib.auth.hashers.MD5PasswordHasher' not in hashers


def test_production_settings_does_not_use_md5_hasher(monkeypatch):
    prod_settings = load_production_settings(monkeypatch, {
        'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
        'ALLOWED_HOSTS': 'example.com',
    })
    hashers = getattr(prod_settings, 'PASSWORD_HASHERS', None)
    if hashers:
        assert 'django.contrib.auth.hashers.MD5PasswordHasher' not in hashers


def load_local_settings(monkeypatch, env_vars=None):
    """Helper to reload local settings cleanly with specific env vars."""
    monkeypatch.setattr('environ.Env.read_env', lambda *a, **kw: None)
    monkeypatch.delenv('AUTH_THROTTLE_RATE', raising=False)

    if env_vars:
        for k, v in env_vars.items():
            monkeypatch.setenv(k, v)

    for mod in ['config.settings.local', 'config.settings.base']:
        if mod in sys.modules:
            del sys.modules[mod]

    return importlib.import_module('config.settings.local')


def test_production_auth_throttle_rate_default(monkeypatch):
    prod_settings = load_production_settings(monkeypatch, {
        'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
        'ALLOWED_HOSTS': 'example.com',
    })
    assert prod_settings.AUTH_THROTTLE_RATE == '5/minute'
    assert prod_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth'] == '5/minute'


def test_production_auth_throttle_rate_custom(monkeypatch):
    prod_settings = load_production_settings(monkeypatch, {
        'SECRET_KEY': 'valid-production-secret-key-for-test-12345',
        'ALLOWED_HOSTS': 'example.com',
        'AUTH_THROTTLE_RATE': '20/minute',
    })
    assert prod_settings.AUTH_THROTTLE_RATE == '20/minute'
    assert prod_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth'] == '20/minute'


def test_local_auth_throttle_rate_default(monkeypatch):
    local_settings = load_local_settings(monkeypatch)
    assert local_settings.AUTH_THROTTLE_RATE == '100/minute'
    assert local_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth'] == '100/minute'


def test_local_auth_throttle_rate_custom(monkeypatch):
    local_settings = load_local_settings(monkeypatch, {
        'AUTH_THROTTLE_RATE': '250/minute',
    })
    assert local_settings.AUTH_THROTTLE_RATE == '250/minute'
    assert local_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth'] == '250/minute'


def test_test_auth_throttle_rate_disabled_in_test_settings():
    test_settings = importlib.import_module('config.settings.test')
    assert getattr(test_settings, 'AUTH_THROTTLE_RATE', None) is None
    assert test_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth'] is None


