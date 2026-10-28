from unittest.mock import MagicMock, patch

import pytest

from apps.coach.models import ChatMessage
from apps.coach.services.client import (
    CoachUnavailableError,
    CoachUpstreamError,
    GeminiCoachService,
    get_remaining_daily_quota,
)


@pytest.mark.django_db
class TestCoachServices:
    def test_is_configured_false_when_project_empty(self, settings):
        settings.GOOGLE_CLOUD_PROJECT = ""
        service = GeminiCoachService()
        assert service.is_configured() is False

    def test_is_configured_false_when_credentials_file_missing(self, settings, tmp_path):
        settings.GOOGLE_CLOUD_PROJECT = "test-project"
        settings.GOOGLE_APPLICATION_CREDENTIALS = str(tmp_path / "nonexistent.json")
        service = GeminiCoachService()
        assert service.is_configured() is False

    def test_is_configured_true_when_configured(self, settings, tmp_path):
        creds_file = tmp_path / "gcp-creds.json"
        creds_file.write_text('{"type": "service_account"}')
        settings.GOOGLE_CLOUD_PROJECT = "test-project"
        settings.GOOGLE_APPLICATION_CREDENTIALS = str(creds_file)
        service = GeminiCoachService()
        assert service.is_configured() is True

    def test_generate_reply_raises_unavailable_when_not_configured(self, user, settings):
        settings.GOOGLE_CLOUD_PROJECT = ""
        service = GeminiCoachService()
        with pytest.raises(CoachUnavailableError):
            service.generate_reply(user, "Hello")

    @patch("apps.coach.services.client.genai.Client")
    def test_generate_reply_success(self, mock_client_cls, user, settings, tmp_path):
        creds_file = tmp_path / "gcp-creds.json"
        creds_file.write_text("{}")
        settings.GOOGLE_CLOUD_PROJECT = "test-project"
        settings.GOOGLE_APPLICATION_CREDENTIALS = str(creds_file)

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "Great job on your water habit! Keep it up."
        mock_response.function_calls = None
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiCoachService()
        reply, pending_action = service.generate_reply(user, "How is my progress?")

        assert reply == "Great job on your water habit! Keep it up."
        assert pending_action is None
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == settings.GEMINI_MODEL
        # Verify prompt delimiters
        contents = call_kwargs["contents"]
        last_content = contents[-1]
        assert "<user_context>" in last_content.parts[0].text
        assert "<user_message>" in last_content.parts[0].text
        assert "How is my progress?" in last_content.parts[0].text

    @patch("apps.coach.services.client.genai.Client")
    def test_generate_reply_with_function_call_creates_pending_action(
        self, mock_client_cls, user, settings, tmp_path
    ):
        creds_file = tmp_path / "gcp-creds.json"
        creds_file.write_text("{}")
        settings.GOOGLE_CLOUD_PROJECT = "test-project"
        settings.GOOGLE_APPLICATION_CREDENTIALS = str(creds_file)

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = ""
        mock_fc = MagicMock()
        mock_fc.name = "create_habit"
        mock_fc.args = {"name": "Evening Stretch", "habit_type": "boolean"}
        mock_response.function_calls = [mock_fc]
        mock_client.models.generate_content.return_value = mock_response

        service = GeminiCoachService()
        reply, pending_action = service.generate_reply(user, "Add a stretch habit")

        assert pending_action is not None
        assert pending_action.action_type == "create_habit"
        assert pending_action.status == "pending"
        assert pending_action.payload["name"] == "Evening Stretch"
        assert "Create habit: Evening Stretch" in pending_action.summary
        assert "Evening Stretch" in reply

    @patch("apps.coach.services.client.genai.Client")
    def test_generate_reply_upstream_error(self, mock_client_cls, user, settings, tmp_path):
        creds_file = tmp_path / "gcp-creds.json"
        creds_file.write_text("{}")
        settings.GOOGLE_CLOUD_PROJECT = "test-project"
        settings.GOOGLE_APPLICATION_CREDENTIALS = str(creds_file)

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("Vertex AI connection timeout")

        service = GeminiCoachService()
        with pytest.raises(CoachUpstreamError):
            service.generate_reply(user, "Hello")

    def test_remaining_daily_quota_calculation(self, user):
        assert get_remaining_daily_quota(user) == 20

        # Create 5 user messages
        for i in range(5):
            ChatMessage.objects.create(
                user=user,
                role=ChatMessage.ROLE_USER,
                content=f"Message {i}",
            )
        # Assistant messages should not count against quota
        for i in range(5):
            ChatMessage.objects.create(
                user=user,
                role=ChatMessage.ROLE_ASSISTANT,
                content=f"Reply {i}",
            )

        assert get_remaining_daily_quota(user) == 15

    def test_remaining_daily_quota_exhausted(self, user):
        for i in range(20):
            ChatMessage.objects.create(
                user=user,
                role=ChatMessage.ROLE_USER,
                content=f"Message {i}",
            )
        assert get_remaining_daily_quota(user) == 0
