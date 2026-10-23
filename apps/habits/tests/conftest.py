import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.habits.models import Habit

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(
        email='testuser@example.com',
        password='password123'
    )

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def habit(user):
    return Habit.objects.create(
        user=user,
        name="Drink Water",
        description="Drink at least 2 liters of water daily",
        color="#3B82F6",
        emoji="💧",
    )
