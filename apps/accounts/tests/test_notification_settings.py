from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestUserNotificationSettings:
    """Test user notification master switch and weekly summary on model and profile API endpoint."""

    def test_user_default_notification_settings(self):
        user = User.objects.create_user(email="testuser@example.com", password="Password123!")
        assert user.notifications_enabled is True
        assert user.weekly_summary_enabled is False

    def test_get_profile_returns_notification_settings(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="Password123!",
            notifications_enabled=True,
            weekly_summary_enabled=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/auth/profile/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["notifications_enabled"] is True
        assert data["weekly_summary_enabled"] is True

    def test_patch_profile_updates_notification_settings(self):
        user = User.objects.create_user(email="testuser@example.com", password="Password123!")
        client = APIClient()
        client.force_authenticate(user=user)

        payload = {
            "notifications_enabled": False,
            "weekly_summary_enabled": True,
        }
        response = client.patch("/api/v1/auth/profile/", payload)
        assert response.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.notifications_enabled is False
        assert user.weekly_summary_enabled is True
