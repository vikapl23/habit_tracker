from datetime import time
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.coach.services.actions import (
    ActionRegistry,
    ArchiveHabitAction,
    CreateHabitAction,
    UpdateHabitAction,
    default_action_registry,
)
from apps.habits.models import Habit


@pytest.mark.django_db
class TestCoachActions:
    def test_registry_registration(self):
        registry = ActionRegistry()
        action = CreateHabitAction()
        registry.register(action)
        assert registry.get("create_habit") == action
        assert registry.get("nonexistent") is None

        tools = registry.get_tools()
        assert len(tools) == 1
        assert len(tools[0].function_declarations) == 1
        assert tools[0].function_declarations[0].name == "create_habit"

    def test_default_registry_has_phase10_actions(self):
        assert default_action_registry.get("create_habit") is not None
        assert default_action_registry.get("update_habit") is not None
        assert default_action_registry.get("archive_habit") is not None

    def test_create_habit_action_validation_and_execution(self, user):
        action = CreateHabitAction()
        # 1. Valid boolean habit
        payload = {
            "name": "Morning Walk",
            "habit_type": "boolean",
            "frequency_type": "daily",
            "reminder_enabled": True,
            "reminder_time": "08:15",
        }
        cleaned = action.validate(user, payload)
        summary = action.get_summary(cleaned)
        assert "Create habit: Morning Walk" in summary
        assert "reminder 08:15" in summary

        result = action.execute(user, cleaned)
        assert result["habit_id"] is not None
        habit = Habit.objects.get(id=result["habit_id"])
        assert habit.name == "Morning Walk"
        assert habit.user == user
        assert habit.reminder_time == time(8, 15)

    def test_create_measurable_habit_action(self, user):
        action = CreateHabitAction()
        payload = {
            "name": "Drink Water",
            "habit_type": "measurable",
            "target_value": 8.0,
            "unit": "glasses",
            "frequency_type": "custom",
            "frequency_days": [0, 2, 4],
        }
        cleaned = action.validate(user, payload)
        summary = action.get_summary(cleaned)
        assert "8.0 glasses" in summary

        result = action.execute(user, cleaned)
        habit = Habit.objects.get(id=result["habit_id"])
        assert habit.habit_type == "measurable"
        assert habit.target_value == Decimal("8.00")
        assert habit.unit == "glasses"

    def test_create_habit_validation_failures(self, user):
        action = CreateHabitAction()
        # Missing name
        with pytest.raises(ValidationError):
            action.validate(user, {"name": ""})

        # Measurable without unit
        with pytest.raises(ValidationError):
            action.validate(
                user,
                {"name": "Water", "habit_type": "measurable", "target_value": 5},
            )

        # Invalid reminder minutes
        with pytest.raises(ValidationError):
            action.validate(
                user,
                {
                    "name": "Walk",
                    "reminder_enabled": True,
                    "reminder_time": "08:12",
                },
            )

    def test_update_habit_action(self, user, other_user):
        habit = Habit.objects.create(
            user=user,
            name="Read Books",
            habit_type="measurable",
            target_value=Decimal("10.00"),
            unit="pages",
        )
        action = UpdateHabitAction()

        # Update target
        payload = {
            "habit_id": habit.id,
            "target_value": 20.0,
            "reminder_enabled": True,
            "reminder_time": "21:00",
        }
        cleaned = action.validate(user, payload)
        summary = action.get_summary(cleaned)
        assert "Update habit: Read Books" in summary

        result = action.execute(user, cleaned)
        assert result["habit_id"] == habit.id
        habit.refresh_from_db()
        assert habit.target_value == Decimal("20.00")
        assert habit.reminder_time == time(21, 0)

        # Rejects updating another user's habit
        other_habit = Habit.objects.create(user=other_user, name="Secret")
        with pytest.raises(ValidationError):
            action.validate(user, {"habit_id": other_habit.id, "name": "Hacked"})

    def test_archive_habit_action(self, user, other_user):
        habit = Habit.objects.create(user=user, name="Old Habit")
        action = ArchiveHabitAction()

        cleaned = action.validate(user, {"habit_id": habit.id})
        summary = action.get_summary(cleaned)
        assert "Archive habit: Old Habit" in summary

        result = action.execute(user, cleaned)
        assert result["habit_id"] == habit.id
        habit.refresh_from_db()
        assert habit.is_archived is True

        # Rejects archiving other user's habit
        other_habit = Habit.objects.create(user=other_user, name="Other")
        with pytest.raises(ValidationError):
            action.validate(user, {"habit_id": other_habit.id})
