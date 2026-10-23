import pytest
from freezegun import freeze_time

from apps.habits.models import Habit
from apps.habits.serializers import HabitSerializer


@pytest.mark.django_db
def test_habit_serializer_default_frequency_representation(habit):
    serializer = HabitSerializer(habit)
    assert serializer.data["frequency_type"] == "daily"
    assert serializer.data["frequency_days"] == []
    assert serializer.data["is_scheduled_today"] is True


@pytest.mark.django_db
def test_habit_serializer_custom_frequency_representation(user):
    # Mon (0), Wed (2), Fri (4)
    habit = Habit.objects.create(
        user=user,
        name="Gym",
        frequency_type="custom",
        frequency_days=[0, 2, 4],
    )
    # Friday 2026-10-23 (weekday 4) -> scheduled
    with freeze_time("2026-10-23 12:00:00"):
        serializer = HabitSerializer(habit)
        assert serializer.data["frequency_type"] == "custom"
        assert serializer.data["frequency_days"] == [0, 2, 4]
        assert serializer.data["is_scheduled_today"] is True

    # Saturday 2026-10-24 (weekday 5) -> off-schedule
    with freeze_time("2026-10-24 12:00:00"):
        serializer = HabitSerializer(habit)
        assert serializer.data["is_scheduled_today"] is False


@pytest.mark.django_db
def test_habit_serializer_valid_custom_frequency_deserialization(user):
    data = {
        "name": "Gym Mon-Fri",
        "color": "#10B981",
        "emoji": "🏋️",
        "frequency_type": "custom",
        "frequency_days": [0, 1, 2, 3, 4],
    }
    serializer = HabitSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    habit = serializer.save(user=user)
    assert habit.frequency_type == "custom"
    assert habit.frequency_days == [0, 1, 2, 3, 4]


@pytest.mark.django_db
def test_habit_serializer_support_shorthand_frequency_list(user):
    """Support frequency=[0, 1, 2, 3, 4] as shorthand for custom frequency."""
    data = {
        "name": "Gym Mon-Fri",
        "frequency": [4, 0, 2],
    }
    serializer = HabitSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    habit = serializer.save(user=user)
    assert habit.frequency_type == "custom"
    assert habit.frequency_days == [0, 2, 4]


@pytest.mark.django_db
def test_habit_serializer_support_shorthand_frequency_daily(user):
    """Support frequency='daily' as shorthand for daily frequency."""
    data = {
        "name": "Daily Water",
        "frequency": "daily",
    }
    serializer = HabitSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    habit = serializer.save(user=user)
    assert habit.frequency_type == "daily"
    assert habit.frequency_days == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload,error_field",
    [
        ({"frequency_type": "custom", "frequency_days": []}, "frequency_days"),
        ({"frequency_type": "custom"}, "frequency_days"),
        ({"frequency_type": "custom", "frequency_days": [-1]}, "frequency_days"),
        ({"frequency_type": "custom", "frequency_days": [7]}, "frequency_days"),
        ({"frequency_type": "custom", "frequency_days": [1, 1, 2]}, "frequency_days"),
        ({"frequency_type": "custom", "frequency_days": ["monday"]}, "frequency_days"),
        ({"frequency_type": "custom", "frequency_days": [True]}, "frequency_days"),
        ({"frequency_type": "invalid_type", "frequency_days": [0]}, "frequency_type"),
        ({"frequency": []}, "frequency"),
        ({"frequency": [8]}, "frequency"),
        ({"frequency": "monthly"}, "frequency"),
    ],
)
def test_habit_serializer_validation_errors(payload, error_field):
    data = {"name": "Test Habit", **payload}
    serializer = HabitSerializer(data=data)
    assert not serializer.is_valid()
    assert error_field in serializer.errors


@pytest.mark.django_db
def test_habit_serializer_normalizes_daily_frequency_days(user):
    data = {
        "name": "Read Book",
        "frequency_type": "daily",
        "frequency_days": [0, 1, 2],
    }
    serializer = HabitSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    habit = serializer.save(user=user)
    assert habit.frequency_type == "daily"
    assert habit.frequency_days == []


@pytest.mark.django_db
def test_habit_serializer_update_frequency(user):
    habit = Habit.objects.create(user=user, name="Meditation", frequency_type="daily")
    serializer = HabitSerializer(
        instance=habit,
        data={"frequency_type": "custom", "frequency_days": [1, 3, 5]},
        partial=True,
    )
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()
    assert updated.frequency_type == "custom"
    assert updated.frequency_days == [1, 3, 5]
