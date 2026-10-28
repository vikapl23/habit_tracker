from datetime import timedelta

import pytest
from django.utils import timezone

from apps.coach.models import ChatMessage, PendingAction


@pytest.mark.django_db
class TestCoachModels:
    def test_create_chat_message(self, user):
        msg = ChatMessage.objects.create(
            user=user,
            role="user",
            content="Hello coach!",
        )
        assert msg.id is not None
        assert msg.user == user
        assert msg.role == "user"
        assert msg.content == "Hello coach!"
        assert str(msg) == f"user: Hello coach! ({user.email})"

    def test_create_pending_action(self, user):
        now = timezone.now()
        expires_at = now + timedelta(minutes=15)
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Meditation", "target_value": 5, "unit": "minutes"},
            summary="Create habit: Meditation, 5 minutes",
            expires_at=expires_at,
        )
        assert action.id is not None
        assert action.status == "pending"
        assert action.action_type == "create_habit"
        assert action.payload["name"] == "Meditation"
        assert action.is_expired() is False

    def test_pending_action_expiration_check(self, user):
        past = timezone.now() - timedelta(minutes=1)
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Meditation"},
            summary="Create habit: Meditation",
            expires_at=past,
        )
        assert action.is_expired() is True

    def test_chat_message_with_pending_action(self, user):
        action = PendingAction.objects.create(
            user=user,
            action_type="create_habit",
            payload={"name": "Reading"},
            summary="Create habit: Reading",
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        msg = ChatMessage.objects.create(
            user=user,
            role="assistant",
            content="I can create that for you.",
            pending_action=action,
        )
        assert msg.pending_action == action
        assert action.messages.first() == msg

    def test_user_cascade_deletes_messages(self, user):
        ChatMessage.objects.create(user=user, role="user", content="Hi")
        ChatMessage.objects.create(user=user, role="assistant", content="Hello")
        assert ChatMessage.objects.filter(user=user).count() == 2

        user.delete()
        assert ChatMessage.objects.count() == 0
