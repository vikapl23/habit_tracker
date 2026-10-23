import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.habits.models import Habit

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(email="testuser@example.com", password="password123")


@pytest.fixture
def other_user():
    return User.objects.create_user(email="otheruser@example.com", password="password123")


@pytest.fixture
def unauthenticated_client():
    return APIClient()


@pytest.fixture
def api_client(db, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def auth_client(api_client):
    return api_client


@pytest.fixture
def jwt_client(db, user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def habit(user):
    return Habit.objects.create(
        user=user,
        name="Drink Water",
        description="Drink at least 2 liters of water daily",
        color="#3B82F6",
        emoji="💧",
    )
