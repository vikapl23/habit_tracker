import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def reset_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def existing_user():
    return User.objects.create_user(email="existing@example.com", password="ValidPassword123!")


@pytest.mark.django_db
class TestAuthEndpoints:
    register_url = "/api/v1/auth/register/"
    token_url = "/api/v1/auth/token/"
    refresh_url = "/api/v1/auth/token/refresh/"

    # Registration Tests
    def test_register_success(self, api_client):
        data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "newuser@example.com"
        assert "id" in response.data
        assert "password" not in response.data
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_duplicate_email_fails(self, api_client, existing_user):
        data = {
            "email": existing_user.email,
            "password": "AnotherPassword123!",
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_duplicate_email_case_insensitive_fails(self, api_client, existing_user):
        data = {
            "email": existing_user.email.upper(),
            "password": "AnotherPassword123!",
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_stores_email_lowercased(self, api_client):
        data = {
            "email": "NewUserWithCaps@Example.COM",
            "password": "StrongPassword123!",
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "newuserwithcaps@example.com"
        assert User.objects.filter(email="newuserwithcaps@example.com").exists()

    def test_register_invalid_email_fails(self, api_client):
        data = {
            "email": "not-an-email",
            "password": "StrongPassword123!",
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_missing_fields_fails(self, api_client):
        response = api_client.post(self.register_url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
        assert "password" in response.data

    def test_register_short_password_fails(self, api_client):
        data = {
            "email": "shortpass@example.com",
            "password": "123",
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    @override_settings(AUTH_THROTTLE_RATE="5/minute")
    def test_register_throttling(self, api_client):
        for i in range(5):
            res = api_client.post(
                self.register_url,
                {
                    "email": f"throttle{i}@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert res.status_code == status.HTTP_201_CREATED

        # 6th request from same IP should be throttled
        res = api_client.post(
            self.register_url,
            {
                "email": "throttle_blocked@example.com",
                "password": "StrongPassword123!",
            },
        )
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_auth_endpoints_not_throttled_under_test_settings(self, api_client):
        # In test settings, throttling is disabled or high so multiple auth requests succeed without 429
        for i in range(8):
            res = api_client.post(
                self.register_url,
                {
                    "email": f"unthrottled{i}@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert res.status_code == status.HTTP_201_CREATED

    # Token Obtain Tests
    def test_token_obtain_success(self, api_client, existing_user):
        data = {
            "email": "existing@example.com",
            "password": "ValidPassword123!",
        }
        response = api_client.post(self.token_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_token_obtain_case_insensitive(self, api_client, existing_user):
        data = {
            "email": "ExIsTiNg@EXAMPLE.com",
            "password": "ValidPassword123!",
        }
        response = api_client.post(self.token_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_token_obtain_invalid_credentials_fails(self, api_client, existing_user):
        data = {
            "email": "existing@example.com",
            "password": "WrongPassword!",
        }
        response = api_client.post(self.token_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_obtain_nonexistent_user_fails(self, api_client):
        data = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        }
        response = api_client.post(self.token_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @override_settings(AUTH_THROTTLE_RATE="5/minute")
    def test_token_obtain_throttling(self, api_client, existing_user):
        for _ in range(5):
            res = api_client.post(
                self.token_url,
                {
                    "email": existing_user.email,
                    "password": "ValidPassword123!",
                },
            )
            assert res.status_code == status.HTTP_200_OK

        # 6th request from same IP should be throttled
        res = api_client.post(
            self.token_url,
            {
                "email": existing_user.email,
                "password": "ValidPassword123!",
            },
        )
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @override_settings(AUTH_THROTTLE_RATE="5/minute")
    def test_auth_throttling_shared_between_register_and_token(self, api_client):
        # 3 register requests
        for i in range(3):
            res = api_client.post(
                self.register_url,
                {
                    "email": f"shared{i}@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert res.status_code == status.HTTP_201_CREATED

        # 2 token requests (total 5 requests)
        for i in range(2):
            res = api_client.post(
                self.token_url,
                {
                    "email": f"shared{i}@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert res.status_code == status.HTTP_200_OK

        # 6th auth request from same IP should be throttled
        res = api_client.post(
            self.token_url,
            {
                "email": "shared0@example.com",
                "password": "StrongPassword123!",
            },
        )
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # Token Refresh Tests
    def test_token_refresh_success(self, api_client, existing_user):
        # Obtain tokens first
        token_res = api_client.post(
            self.token_url,
            {
                "email": "existing@example.com",
                "password": "ValidPassword123!",
            },
        )
        refresh_token = token_res.data["refresh"]

        # Refresh
        response = api_client.post(self.refresh_url, {"refresh": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_token_refresh_invalid_token_fails(self, api_client):
        response = api_client.post(self.refresh_url, {"refresh": "invalid.refresh.token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_swagger_schema_includes_jwt_auth(api_client):
    response = api_client.get("/api/schema/")
    assert response.status_code == status.HTTP_200_OK
    assert "jwtAuth" in response.data["components"]["securitySchemes"]
    jwt_scheme = response.data["components"]["securitySchemes"]["jwtAuth"]
    assert jwt_scheme["type"] == "http"
    assert jwt_scheme["scheme"] == "bearer"
    assert jwt_scheme["bearerFormat"] == "JWT"
