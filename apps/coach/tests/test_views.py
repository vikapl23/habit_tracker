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
        mock_generate_reply.return_value = (
            "Great question! Start with 5 minutes.",
            None,
        )

        response = api_client.post(self.url, {"content": "How do I build a habit?"})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["user_message"]["content"] == "How do I build a habit?"
        assert response.data["user_message"]["role"] == "user"
        assert (
            response.data["assistant_message"]["content"] == "Great question! Start with 5 minutes."
        )
        assert response.data["assistant_message"]["role"] == "assistant"
        assert response.data["assistant_message"]["pending_action"] is None
        assert response.data["remaining_messages"] == 19

        # Ensure saved to DB
        assert ChatMessage.objects.filter(user=user).count() == 2

    @patch("apps.coach.views.GeminiCoachService.generate_reply")
    @patch("apps.coach.views.GeminiCoachService.is_configured", return_value=True)
    def test_post_message_with_action_proposal(
        self, mock_is_configured, mock_generate_reply, api_client, user
    ):
        pending_action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Meditation", "habit_type": "boolean"},
            summary="Create habit: Meditation, daily",
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        mock_generate_reply.return_value = (
            "I've proposed a new habit for you!",
            pending_action,
        )

        response = api_client.post(self.url, {"content": "Create a meditation habit"})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["assistant_message"]["pending_action"]["id"] == pending_action.id
        assert response.data["assistant_message"]["pending_action"]["action_type"] == "create_habit"
        assert (
            response.data["assistant_message"]["pending_action"]["summary"]
            == "Create habit: Meditation, daily"
        )

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

    @patch("apps.coach.views.GeminiCoachService.generate_reply")
    @patch("apps.coach.views.GeminiCoachService.is_configured", return_value=True)
    def test_post_message_reserves_quota_before_gemini_call(
        self, mock_is_configured, mock_generate_reply, api_client, user
    ):
        def check_reserved(u, content, **kwargs):
            assert ChatMessage.objects.filter(user=u, role=ChatMessage.ROLE_USER).count() == 1
            return "Reserved reply", None

        mock_generate_reply.side_effect = check_reserved
        response = api_client.post(self.url, {"content": "Checking reservation"})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["remaining_messages"] == 19
        assert ChatMessage.objects.filter(user=user).count() == 2

    @patch("apps.coach.views.GeminiCoachService.generate_reply")
    @patch("apps.coach.views.GeminiCoachService.is_configured", return_value=True)
    def test_post_message_refunds_quota_on_error(
        self, mock_is_configured, mock_generate_reply, api_client, user
    ):
        mock_generate_reply.side_effect = CoachUpstreamError("Timeout")
        response = api_client.post(self.url, {"content": "Should refund"})
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert ChatMessage.objects.filter(user=user).count() == 0
        from apps.coach.services.client import get_remaining_daily_quota

        assert get_remaining_daily_quota(user) == 20

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


@pytest.mark.django_db
class TestCoachActionConfirmAPI:
    def test_unauthenticated_rejected(self, unauthenticated_client):
        response = unauthenticated_client.post("/api/v1/coach/actions/1/confirm/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_confirm_action_not_found(self, api_client):
        response = api_client.post("/api/v1/coach/actions/999/confirm/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_confirm_other_user_action_returns_404(self, api_client, other_user):
        action = PendingAction.objects.create(
            user=other_user,
            action_type="create_habit",
            payload={"name": "Secret", "habit_type": "boolean"},
            summary="Create habit: Secret",
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_confirm_create_habit_action_success(self, api_client, user):
        from apps.habits.models import Habit

        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={
                "name": "Evening Journaling",
                "habit_type": "boolean",
                "frequency_type": "daily",
                "reminder_enabled": True,
                "reminder_time": "22:00",
            },
            summary="Create habit: Evening Journaling, daily, reminder 22:00",
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        response = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "confirmed"
        assert response.data["action_id"] == action.id
        assert response.data["result"]["name"] == "Evening Journaling"

        action.refresh_from_db()
        assert action.status == PendingAction.STATUS_CONFIRMED
        assert action.executed_at is not None

        habit = Habit.objects.get(id=response.data["result"]["habit_id"])
        assert habit.name == "Evening Journaling"
        assert habit.user == user

    def test_confirm_already_confirmed_action_fails(self, api_client, user):
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Reading"},
            status=PendingAction.STATUS_CONFIRMED,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be confirmed" in response.data["detail"]

    def test_confirm_expired_action_fails(self, api_client, user):
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Reading"},
            status=PendingAction.STATUS_PENDING,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in response.data["detail"].lower()

        action.refresh_from_db()
        assert action.status == PendingAction.STATUS_EXPIRED

    def test_confirm_action_already_executing_fails(self, api_client, user):
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Running"},
            status=getattr(PendingAction, "STATUS_EXECUTING", "executing"),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            "cannot be confirmed" in response.data["detail"]
            or "executing" in response.data["detail"]
        )

    def test_confirm_action_concurrent_double_submit_only_one_succeeds(self, api_client, user):
        from apps.habits.models import Habit

        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={
                "name": "Unique Test Habit",
                "habit_type": "boolean",
                "frequency_type": "daily",
            },
            status=PendingAction.STATUS_PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        res1 = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")
        res2 = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")

        assert res1.status_code == status.HTTP_200_OK
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert Habit.objects.filter(user=user, name="Unique Test Habit").count() == 1

    def test_confirm_action_deleted_habit_returns_400_and_marks_failed(self, api_client, user):
        from apps.habits.models import Habit

        habit = Habit.objects.create(user=user, name="To be deleted")
        action = PendingAction.objects.create(
            user=user,
            action_type="archive_habit",
            payload={"habit_id": habit.id},
            status=PendingAction.STATUS_PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        habit.delete()

        response = api_client.post(f"/api/v1/coach/actions/{action.id}/confirm/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

        action.refresh_from_db()
        assert action.status == getattr(PendingAction, "STATUS_FAILED", "failed")


@pytest.mark.django_db
class TestCoachActionCancelAPI:
    def test_unauthenticated_rejected(self, unauthenticated_client):
        response = unauthenticated_client.post("/api/v1/coach/actions/1/cancel/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cancel_action_not_found(self, api_client):
        response = api_client.post("/api/v1/coach/actions/999/cancel/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_other_user_action_returns_404(self, api_client, other_user):
        action = PendingAction.objects.create(
            user=other_user,
            action_type="create_habit",
            payload={"name": "Other Habit"},
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = api_client.post(f"/api/v1/coach/actions/{action.id}/cancel/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_action_success(self, api_client, user):
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Reading"},
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = api_client.post(f"/api/v1/coach/actions/{action.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "cancelled"
        assert response.data["action_id"] == action.id

        action.refresh_from_db()
        assert action.status == PendingAction.STATUS_CANCELLED

    def test_cancel_non_pending_action_fails(self, api_client, user):
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Reading"},
            status=PendingAction.STATUS_CONFIRMED,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = api_client.post(f"/api/v1/coach/actions/{action.id}/cancel/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be cancelled" in response.data["detail"]
