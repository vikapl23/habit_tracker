import importlib
import sys
import pytest
from django.core.exceptions import ImproperlyConfigured


def load_production_settings(monkeypatch, env_vars=None):
    """Helper to reload production settings cleanly with specific env vars."""
    monkeypatch.setattr('environ.Env.read_env', lambda *a, **kw: None)
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('ALLOWED_HOSTS', raising=False)

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
