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
