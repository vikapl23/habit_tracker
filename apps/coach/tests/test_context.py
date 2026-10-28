from datetime import time, timedelta
from decimal import Decimal

import pytest

from apps.coach.models import ChatMessage
from apps.coach.services.context import build_coach_context, format_conversation_history
from apps.habits.models import Habit, HabitCheckIn


@pytest.mark.django_db
class TestCoachContext:
    def test_context_with_no_habits(self, user):
        context = build_coach_context(user)
        assert "Active Habits:" in context
        assert "No active habits found." in context

    def test_context_with_boolean_and_measurable_habits(self, user):
        today = user.get_today()
        # Boolean habit
        h1 = Habit.objects.create(
            user=user,
            name="Morning Run",
            habit_type="boolean",
            frequency_type="daily",
            reminder_enabled=True,
            reminder_time=time(7, 30),
        )
        for i in range(4):
            HabitCheckIn.objects.create(
                habit=h1, date=today - timedelta(days=i), value=Decimal("1.00")
            )

        # Measurable habit
        h2 = Habit.objects.create(
            user=user,
            name="Drink Water",
            habit_type="measurable",
            target_value=Decimal("8.00"),
            unit="glasses",
            frequency_type="custom",
            frequency_days=[0, 2, 4],  # Mon, Wed, Fri
            reminder_enabled=False,
        )
        HabitCheckIn.objects.create(habit=h2, date=today, value=Decimal("4.00"))

        context = build_coach_context(user)

        # Verify Habit 1
        assert "Morning Run" in context
        assert "Type: boolean" in context
        assert "Target: N/A" in context
        assert "Frequency: daily" in context
        assert "Streak: current 4, longest 4" in context
        assert "Reminder: 07:30" in context
        assert "Today: completed (1.0/1.0)" in context

        # Verify Habit 2
        assert "Drink Water" in context
        assert "Type: measurable" in context
        assert "Target: 8.0 glasses" in context
        assert "Frequency: custom (Mon, Wed, Fri)" in context
        assert "Reminder: none" in context
        assert "Today: in progress (4.0 / 8.0 glasses, 50%)" in context
        assert "7d Completion:" in context
        assert "30d Completion:" in context

    def test_archived_habits_excluded_from_context(self, user):
        Habit.objects.create(
            user=user,
            name="Archived Habit",
            is_archived=True,
        )
        Habit.objects.create(
            user=user,
            name="Active Habit",
            is_archived=False,
        )
        context = build_coach_context(user)
        assert "Active Habit" in context
        assert "Archived Habit" not in context

    def test_other_user_habits_excluded(self, user, other_user):
        Habit.objects.create(user=other_user, name="Secret Other Habit")
        Habit.objects.create(user=user, name="My Habit")

        context = build_coach_context(user)
        assert "My Habit" in context
        assert "Secret Other Habit" not in context

    def test_conversation_history_last_10_messages(self, user):
        for i in range(15):
            role = "user" if i % 2 == 0 else "assistant"
            ChatMessage.objects.create(
                user=user,
                role=role,
                content=f"Message {i}",
            )

        history = format_conversation_history(user, limit=10)
        assert len(history) == 10
        # Should contain message 5 to 14, but not message 0 to 4
        assert history[0]["content"] == "Message 5"
        assert history[-1]["content"] == "Message 14"
