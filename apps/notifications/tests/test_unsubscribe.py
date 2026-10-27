from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.tokens import generate_unsubscribe_token, verify_unsubscribe_token

User = get_user_model()


@pytest.mark.django_db
class TestUnsubscribe:
    def test_generate_and_verify_token(self):
        user = User.objects.create_user(email="user@example.com", password="Password123!")
        token = generate_unsubscribe_token(user)
        assert isinstance(token, str)

        user_id = verify_unsubscribe_token(token)
        assert user_id == user.pk

    def test_verify_invalid_or_tampered_token(self):
        user = User.objects.create_user(email="user@example.com", password="Password123!")
        token = generate_unsubscribe_token(user)
        tampered = token + "xyz"
        assert verify_unsubscribe_token(tampered) is None
        assert verify_unsubscribe_token("completely-invalid") is None

    def test_unsubscribe_endpoint_turns_off_notifications_enabled(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="Password123!",
            notifications_enabled=True,
            weekly_summary_enabled=True,
        )
        token = generate_unsubscribe_token(user)

        client = APIClient()
        response = client.get(f"/api/v1/notifications/unsubscribe/{token}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["unsubscribed"] is True

        user.refresh_from_db()
        assert user.notifications_enabled is False

    def test_unsubscribe_endpoint_invalid_token_returns_400(self):
        client = APIClient()
        response = client.get("/api/v1/notifications/unsubscribe/invalid-token-123/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.json()

    def test_unsubscribe_endpoint_nonexistent_user_returns_404(self):
        user = User.objects.create_user(email="user@example.com", password="Password123!")
        token = generate_unsubscribe_token(user)
        user.delete()

        client = APIClient()
        response = client.get(f"/api/v1/notifications/unsubscribe/{token}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
