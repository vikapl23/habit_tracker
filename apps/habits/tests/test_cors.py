import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_cors_headers_allowed_origin():
    client = APIClient()
    response = client.get("/api/v1/auth/token/", HTTP_ORIGIN="http://localhost:5173")
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"


@pytest.mark.django_db
def test_cors_headers_disallowed_origin():
    client = APIClient()
    response = client.get("/api/v1/auth/token/", HTTP_ORIGIN="http://disallowed-origin.com")
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.django_db
def test_cors_preflight_options_allowed_origin():
    client = APIClient()
    response = client.options(
        "/api/v1/auth/token/",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,authorization",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "POST" in response.headers.get("Access-Control-Allow-Methods", "")


@pytest.mark.django_db
def test_cors_preflight_options_disallowed_origin():
    client = APIClient()
    response = client.options(
        "/api/v1/auth/token/",
        HTTP_ORIGIN="http://disallowed-origin.com",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_allowed_origins_default_setting(settings):
    assert "http://localhost:5173" in settings.CORS_ALLOWED_ORIGINS
