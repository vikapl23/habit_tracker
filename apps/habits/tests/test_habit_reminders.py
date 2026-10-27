from __future__ import annotations

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient

from apps.habits.models import Habit

User = get_user_model()


@pytest.mark.django_db
class TestHabitReminderModelAndValidation:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(email="habitreminders@example.com", password="Password123!")

    def test_habit_default_reminder_fields(self, user):
        habit = Habit.objects.create(user=user, name="Morning Run")
        assert habit.reminder_enabled is False
        assert habit.reminder_time is None

    def test_reminder_time_required_when_reminder_enabled(self, user):
        habit = Habit(user=user, name="Evening Reading", reminder_enabled=True, reminder_time=None)
        with pytest.raises(ValidationError) as exc_info:
            habit.full_clean()
        assert "reminder_time" in exc_info.value.message_dict

    @pytest.mark.parametrize("invalid_minute", [1, 7, 14, 16, 29, 31, 44, 46, 59])
    def test_reminder_time_minutes_must_be_0_15_30_45(self, user, invalid_minute):
        habit = Habit(
            user=user,
            name="Stretching",
            reminder_enabled=True,
            reminder_time=datetime.time(8, invalid_minute),
        )
        with pytest.raises(ValidationError) as exc_info:
            habit.full_clean()
        assert "reminder_time" in exc_info.value.message_dict

    @pytest.mark.parametrize("valid_minute", [0, 15, 30, 45])
    def test_reminder_time_valid_quarter_hours(self, user, valid_minute):
        habit = Habit(
            user=user,
            name="Water",
            reminder_enabled=True,
            reminder_time=datetime.time(10, valid_minute),
        )
        habit.full_clean()
        habit.save()
        assert habit.reminder_enabled is True
        assert habit.reminder_time == datetime.time(10, valid_minute)


@pytest.mark.django_db
class TestHabitReminderAPI:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(email="apiuser@example.com", password="Password123!")

    @pytest.fixture
    def auth_client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_create_habit_with_reminder(self, auth_client):
        payload = {
            "name": "Meditation",
            "reminder_enabled": True,
            "reminder_time": "08:15:00",
        }
        response = auth_client.post("/api/v1/habits/", payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["reminder_enabled"] is True
        assert data["reminder_time"] in ("08:15:00", "08:15")

    def test_create_habit_reminder_enabled_without_time_fails(self, auth_client):
        payload = {
            "name": "Meditation",
            "reminder_enabled": True,
        }
        response = auth_client.post("/api/v1/habits/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "reminder_time" in response.json()

    def test_create_habit_invalid_reminder_minute_fails(self, auth_client):
        payload = {
            "name": "Meditation",
            "reminder_enabled": True,
            "reminder_time": "08:10:00",
        }
        response = auth_client.post("/api/v1/habits/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "reminder_time" in response.json()

    def test_update_habit_reminder(self, auth_client, user):
        habit = Habit.objects.create(
            user=user,
            name="Workout",
            reminder_enabled=False,
        )
        payload = {
            "reminder_enabled": True,
            "reminder_time": "18:45:00",
        }
        response = auth_client.patch(f"/api/v1/habits/{habit.id}/", payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["reminder_enabled"] is True
        assert data["reminder_time"] in ("18:45:00", "18:45")

        habit.refresh_from_db()
        assert habit.reminder_enabled is True
        assert habit.reminder_time == datetime.time(18, 45)
