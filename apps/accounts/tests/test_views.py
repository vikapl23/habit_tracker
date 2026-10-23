import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def existing_user():
    return User.objects.create_user(
        email='existing@example.com',
        password='ValidPassword123!'
    )


@pytest.mark.django_db
class TestAuthEndpoints:
    register_url = '/api/v1/auth/register/'
    token_url = '/api/v1/auth/token/'
    refresh_url = '/api/v1/auth/token/refresh/'

    # Registration Tests
    def test_register_success(self, api_client):
        data = {
            'email': 'newuser@example.com',
            'password': 'StrongPassword123!',
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'newuser@example.com'
        assert 'id' in response.data
        assert 'password' not in response.data
        assert User.objects.filter(email='newuser@example.com').exists()

    def test_register_duplicate_email_fails(self, api_client, existing_user):
        data = {
            'email': existing_user.email,
            'password': 'AnotherPassword123!',
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_register_invalid_email_fails(self, api_client):
        data = {
            'email': 'not-an-email',
            'password': 'StrongPassword123!',
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_register_missing_fields_fails(self, api_client):
        response = api_client.post(self.register_url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
        assert 'password' in response.data

    def test_register_short_password_fails(self, api_client):
        data = {
            'email': 'shortpass@example.com',
            'password': '123',
        }
        response = api_client.post(self.register_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    # Token Obtain Tests
    def test_token_obtain_success(self, api_client, existing_user):
        data = {
            'email': 'existing@example.com',
            'password': 'ValidPassword123!',
        }
        response = api_client.post(self.token_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_token_obtain_invalid_credentials_fails(self, api_client, existing_user):
        data = {
            'email': 'existing@example.com',
            'password': 'WrongPassword!',
        }
        response = api_client.post(self.token_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_obtain_nonexistent_user_fails(self, api_client):
        data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!',
        }
        response = api_client.post(self.token_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Token Refresh Tests
    def test_token_refresh_success(self, api_client, existing_user):
        # Obtain tokens first
        token_res = api_client.post(self.token_url, {
            'email': 'existing@example.com',
            'password': 'ValidPassword123!',
        })
        refresh_token = token_res.data['refresh']

        # Refresh
        response = api_client.post(self.refresh_url, {'refresh': refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_token_refresh_invalid_token_fails(self, api_client):
        response = api_client.post(self.refresh_url, {'refresh': 'invalid.refresh.token'})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_swagger_schema_includes_jwt_auth(api_client):
    response = api_client.get('/api/schema/')
    assert response.status_code == status.HTTP_200_OK
    assert 'jwtAuth' in response.data['components']['securitySchemes']
    jwt_scheme = response.data['components']['securitySchemes']['jwtAuth']
    assert jwt_scheme['type'] == 'http'
    assert jwt_scheme['scheme'] == 'bearer'
    assert jwt_scheme['bearerFormat'] == 'JWT'
