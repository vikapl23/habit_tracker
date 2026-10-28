import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="coachuser@example.com",
        password="password123",
        timezone="UTC",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="othercoachuser@example.com",
        password="password123",
        timezone="UTC",
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_client():
    return APIClient()
