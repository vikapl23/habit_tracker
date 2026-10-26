from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestInternalSendNotificationsEndpoint:
    def test_missing_cron_token_header_returns_403(self):
        client = APIClient()
        response = client.post("/api/v1/internal/send-notifications/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "detail" in response.json()

    def test_wrong_cron_token_header_returns_403(self):
        client = APIClient()
        response = client.post(
            "/api/v1/internal/send-notifications/",
            HTTP_X_CRON_TOKEN="wrong-token-value",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "detail" in response.json()

    def test_server_cron_token_not_set_returns_403(self, settings):
        settings.CRON_TOKEN = ""
        client = APIClient()
        response = client.post(
            "/api/v1/internal/send-notifications/",
            HTTP_X_CRON_TOKEN="some-token",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("apps.notifications.views.send_due_notifications")
    def test_valid_cron_token_header_succeeds(self, mock_send, settings):
        settings.CRON_TOKEN = "super-secret-cron-token"
        mock_send.return_value = {
            "daily_reminders_sent": 3,
            "weekly_summaries_sent": 2,
            "total_sent": 5,
        }

        client = APIClient()
        response = client.post(
            "/api/v1/internal/send-notifications/",
            HTTP_X_CRON_TOKEN="super-secret-cron-token",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["daily_reminders_sent"] == 3
        assert data["weekly_summaries_sent"] == 2
        assert data["total_sent"] == 5
        mock_send.assert_called_once_with(force=False)

    @patch("apps.notifications.views.send_due_notifications")
    def test_valid_cron_token_with_force_flag(self, mock_send, settings):
        settings.CRON_TOKEN = "super-secret-cron-token"
        mock_send.return_value = {
            "daily_reminders_sent": 1,
            "weekly_summaries_sent": 0,
            "total_sent": 1,
        }

        client = APIClient()
        response = client.post(
            "/api/v1/internal/send-notifications/",
            {"force": True},
            format="json",
            HTTP_X_CRON_TOKEN="super-secret-cron-token",
        )
        assert response.status_code == status.HTTP_200_OK
        mock_send.assert_called_once_with(force=True)


@pytest.mark.django_db
class TestSendNotificationsManagementCommand:
    @patch("apps.notifications.management.commands.send_notifications.send_due_notifications")
    def test_command_without_force(self, mock_send):
        mock_send.return_value = {
            "daily_reminders_sent": 2,
            "weekly_summaries_sent": 1,
            "total_sent": 3,
        }
        out = io.StringIO()
        call_command("send_notifications", stdout=out)
        mock_send.assert_called_once_with(force=False)
        output = out.getvalue()
        assert "3 notifications sent" in output

    @patch("apps.notifications.management.commands.send_notifications.send_due_notifications")
    def test_command_with_force(self, mock_send):
        mock_send.return_value = {
            "daily_reminders_sent": 0,
            "weekly_summaries_sent": 0,
            "total_sent": 0,
        }
        out = io.StringIO()
        call_command("send_notifications", "--force", stdout=out)
        mock_send.assert_called_once_with(force=True)
        output = out.getvalue()
        assert "0 notifications sent" in output
