from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from apps.coach.models import ChatMessage, PendingAction
from apps.coach.services.client import CoachUpstreamError


@pytest.mark.django_db
class TestCoachMessagesAPI:
    url = "/api/v1/coach/messages/"

    def test_unauthenticated_request_rejected(self, unauthenticated_client):
        response = unauthenticated_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = unauthenticated_client.post(self.url, {"content": "Hi"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = unauthenticated_client.delete(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_messages_empty(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["remaining_messages"] == 20
        assert response.data["daily_limit"] == 20
        assert response.data["results"] == []

    def test_get_messages_with_history(self, api_client, user):
        ChatMessage.objects.create(user=user, role="user", content="Hello")
        ChatMessage.objects.create(user=user, role="assistant", content="Hi there!")

        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["remaining_messages"] == 19
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["content"] == "Hello"
        assert response.data["results"][0]["role"] == "user"
        assert response.data["results"][1]["content"] == "Hi there!"
        assert response.data["results"][1]["role"] == "assistant"

    def test_get_messages_user_isolation(self, api_client, other_user):
        ChatMessage.objects.create(user=other_user, role="user", content="Other message")
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_post_message_max_length_exceeded(self, api_client):
        long_content = "a" * 1001
        response = api_client.post(self.url, {"content": long_content})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "content" in response.data

    def test_post_message_empty(self, api_client):
        response = api_client.post(self.url, {"content": "   "})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "content" in response.data

    def test_post_message_503_when_unconfigured(self, api_client, settings):
        settings.GOOGLE_CLOUD_PROJECT = ""
        response = api_client.post(self.url, {"content": "Hello coach"})
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "detail" in response.data
        assert "not configured or currently unavailable" in response.data["detail"]

    @patch("apps.coach.views.GeminiCoachService.generate_reply")
    @patch("apps.coach.views.GeminiCoachService.is_configured", return_value=True)
    def test_post_message_success(self, mock_is_configured, mock_generate_reply, api_client, user):
        mock_generate_reply.return_value = "Great question! Start with 5 minutes."

        response = api_client.post(self.url, {"content": "How do I build a habit?"})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["user_message"]["content"] == "How do I build a habit?"
        assert response.data["user_message"]["role"] == "user"
        assert (
            response.data["assistant_message"]["content"] == "Great question! Start with 5 minutes."
        )
        assert response.data["assistant_message"]["role"] == "assistant"
        assert response.data["remaining_messages"] == 19

        # Ensure saved to DB
        assert ChatMessage.objects.filter(user=user).count() == 2

    @patch("apps.coach.views.GeminiCoachService.generate_reply")
    @patch("apps.coach.views.GeminiCoachService.is_configured", return_value=True)
    def test_post_message_502_upstream_error_does_not_save_assistant_reply(
        self, mock_is_configured, mock_generate_reply, api_client, user
    ):
        mock_generate_reply.side_effect = CoachUpstreamError("Upstream timeout")

        response = api_client.post(self.url, {"content": "Help me out"})
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "detail" in response.data

        # Ensure NO assistant reply saved and user message is not counted
        assert ChatMessage.objects.filter(user=user).count() == 0

    @patch("apps.coach.views.GeminiCoachService.is_configured", return_value=True)
    def test_post_message_429_quota_exhausted(self, mock_is_configured, api_client, user):
        for i in range(20):
            ChatMessage.objects.create(
                user=user,
                role=ChatMessage.ROLE_USER,
                content=f"Message {i}",
            )

        response = api_client.post(self.url, {"content": "One more message"})
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data["remaining_messages"] == 0
        assert "limit reached" in response.data["detail"].lower()

    def test_delete_messages(self, api_client, user):
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Meditation"},
            summary="Create habit: Meditation",
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        ChatMessage.objects.create(user=user, role="user", content="Hello")
        ChatMessage.objects.create(user=user, role="assistant", content="Hi", pending_action=action)

        response = api_client.delete(self.url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert ChatMessage.objects.filter(user=user).count() == 0
        action.refresh_from_db()
        assert action.status == PendingAction.STATUS_CANCELLED
