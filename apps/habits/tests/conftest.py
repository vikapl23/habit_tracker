import pytest
from rest_framework.test import APIClient
from apps.habits.models import Habit

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def habit():
    return Habit.objects.create(
        name="Drink Water",
        description="Drink at least 2 liters of water daily",
        color="#3B82F6",
        emoji="💧",
    )
