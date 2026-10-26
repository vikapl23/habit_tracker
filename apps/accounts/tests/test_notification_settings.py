from __future__ import annotations

import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestUserNotificationSettings:
    """Test user notification preferences on model and profile API endpoint."""

    def test_user_default_notification_settings(self):
        user = User.objects.create_user(email="testuser@example.com", password="Password123!")
        assert user.daily_reminder_enabled is False
        assert user.daily_reminder_time == datetime.time(20, 0)
        assert user.weekly_summary_enabled is False

    def test_get_profile_returns_notification_settings(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="Password123!",
            daily_reminder_enabled=True,
            daily_reminder_time=datetime.time(19, 30),
            weekly_summary_enabled=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/auth/profile/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["daily_reminder_enabled"] is True
        assert data["daily_reminder_time"] == "19:30:00"
        assert data["weekly_summary_enabled"] is True

    def test_patch_profile_updates_notification_settings(self):
        user = User.objects.create_user(email="testuser@example.com", password="Password123!")
        client = APIClient()
        client.force_authenticate(user=user)

        payload = {
            "daily_reminder_enabled": True,
            "daily_reminder_time": "08:15:00",
            "weekly_summary_enabled": True,
        }
        response = client.patch("/api/v1/auth/profile/", payload)
        assert response.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.daily_reminder_enabled is True
        assert user.daily_reminder_time == datetime.time(8, 15)
        assert user.weekly_summary_enabled is True

    def test_patch_profile_invalid_time_returns_400(self):
        user = User.objects.create_user(email="testuser@example.com", password="Password123!")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch("/api/v1/auth/profile/", {"daily_reminder_time": "invalid-time"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "daily_reminder_time" in response.json()
