from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()


@pytest.mark.django_db
class TestJWTAuthenticationFlow:
    def test_jwt_client_fixture_can_list_habits(self, jwt_client, habit):
        res = jwt_client.get('/api/v1/habits/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['count'] == 1
        assert res.data['results'][0]['id'] == habit.id

    def test_invalid_bearer_token_returns_401(self, unauthenticated_client):
        unauthenticated_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_value')
        res = unauthenticated_client.get('/api/v1/habits/')
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert res.data['code'] == 'token_not_valid'

    def test_expired_bearer_token_returns_401(self, unauthenticated_client, user):
        token = AccessToken.for_user(user)
        # Set token expiration in the past
        token.set_exp(lifetime=-timedelta(minutes=10))
        unauthenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token)}')

        res = unauthenticated_client.get('/api/v1/habits/')
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
        assert res.data['code'] == 'token_not_valid'

    def test_end_to_end_auth_and_habit_workflow(self, unauthenticated_client):
        # 1. Register
        reg_res = unauthenticated_client.post('/api/v1/auth/register/', {
            'email': 'e2e@example.com',
            'password': 'SecurePassword123!',
        })
        assert reg_res.status_code == status.HTTP_201_CREATED

        # 2. Obtain token
        token_res = unauthenticated_client.post('/api/v1/auth/token/', {
            'email': 'e2e@example.com',
            'password': 'SecurePassword123!',
        })
        assert token_res.status_code == status.HTTP_200_OK
        access_token = token_res.data['access']
        refresh_token = token_res.data['refresh']

        # 3. Create habit with Bearer token
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        create_res = client.post('/api/v1/habits/', {
            'name': 'E2E Habit',
            'color': '#10B981',
            'emoji': '🚀',
        })
        assert create_res.status_code == status.HTTP_201_CREATED
        habit_id = create_res.data['id']

        # 4. Refresh token
        refresh_res = unauthenticated_client.post('/api/v1/auth/token/refresh/', {
            'refresh': refresh_token,
        })
        assert refresh_res.status_code == status.HTTP_200_OK
        new_access = refresh_res.data['access']

        # 5. Check in with refreshed access token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        check_res = client.post(f'/api/v1/habits/{habit_id}/check/')
        assert check_res.status_code == status.HTTP_201_CREATED
        assert check_res.data['status'] == 'checked'
