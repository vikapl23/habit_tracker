import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import Client, override_settings


def test_healthcheck_endpoint():
    client = Client()
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthcheck_under_production_settings_bypasses_host_and_ssl_redirect():
    """Render health checks call /health/ with Host 'localhost:10000' over plain http.

    Verify that with production settings (SSL redirect enabled, strict ALLOWED_HOSTS):
    1. /health/ with Host localhost:10000 over http returns 200 {"status": "ok"}.
    2. Other paths with Host localhost:10000 return 400 (DisallowedHost).
    3. Other paths over http with valid host return 301 redirect to https.
    """
    prod_middleware = [
        "config.middleware.HealthCheckMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "django.middleware.common.CommonMiddleware",
    ]
    with override_settings(
        MIDDLEWARE=prod_middleware,
        ALLOWED_HOSTS=["example.onrender.com"],
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    ):
        client = Client()

        # 1. Health check over http with localhost:10000 -> 200 {"status": "ok"}
        res_health = client.get("/health/", HTTP_HOST="localhost:10000", secure=False)
        assert res_health.status_code == 200
        assert res_health.json() == {"status": "ok"}

        # 2. Other paths with disallowed host localhost:10000 -> 400 DisallowedHost
        res_disallowed = client.get(
            "/api/v1/auth/login/", HTTP_HOST="localhost:10000", secure=False
        )
        assert res_disallowed.status_code == 400

        # 3. Other paths over http with allowed host -> 301 redirect to https
        res_redirect = client.get("/admin/", HTTP_HOST="example.onrender.com", secure=False)
        assert res_redirect.status_code == 301
        assert res_redirect.headers.get("Location") == "https://example.onrender.com/admin/"


@pytest.fixture(scope="module")
def collected_static():
    """Run collectstatic once into test STATIC_ROOT and clean up after."""
    test_static_root = Path(settings.BASE_DIR) / "test_staticfiles"
    with override_settings(
        DEBUG=False,
        STATIC_ROOT=test_static_root,
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        },
    ):
        call_command("collectstatic", interactive=False, clear=True, verbosity=0)
        yield test_static_root
        if test_static_root.exists():
            shutil.rmtree(test_static_root, ignore_errors=True)


def test_static_files_served_with_debug_false(collected_static):
    """Verify that WhiteNoise serves static files when DEBUG=False."""
    with override_settings(
        DEBUG=False,
        STATIC_ROOT=collected_static,
        ALLOWED_HOSTS=["*"],
    ):
        client = Client()
        # WhiteNoise serves static files at STATIC_URL prefix
        response = client.get("/static/admin/css/base.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("Content-Type", "")
        body = b"".join(response.streaming_content) if response.streaming else response.content
        assert len(body) > 0
