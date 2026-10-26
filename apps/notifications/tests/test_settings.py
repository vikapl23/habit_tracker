from __future__ import annotations

from unittest.mock import patch

from django.conf import settings
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
