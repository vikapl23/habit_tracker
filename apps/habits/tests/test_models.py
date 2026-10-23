from datetime import date, timedelta

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.habits.models import Habit, HabitCheckIn


@pytest.mark.django_db
def test_create_habit(user):
    habit = Habit.objects.create(
        user=user, name="Morning Jog", description="Jog for 30 minutes", color="#10B981", emoji="🏃"
    )
    assert habit.id is not None
    assert habit.name == "Morning Jog"
    assert habit.description == "Jog for 30 minutes"
    assert habit.color == "#10B981"
    assert habit.emoji == "🏃"
    assert habit.is_archived is False
    assert habit.created_at is not None
    assert habit.updated_at is not None
    assert str(habit) == "Morning Jog"


@pytest.mark.django_db
def test_create_checkin(habit):
    checkin_date = date.today()
    checkin = HabitCheckIn.objects.create(habit=habit, date=checkin_date)
    assert checkin.id is not None
    assert checkin.habit == habit
    assert checkin.date == checkin_date
    assert checkin.created_at is not None
    assert f"{habit.name} - {checkin_date}" in str(checkin)


@pytest.mark.django_db
def test_unique_checkin_per_date_constraint(habit):
    checkin_date = date.today()
    HabitCheckIn.objects.create(habit=habit, date=checkin_date)
    with pytest.raises(IntegrityError):
        HabitCheckIn.objects.create(habit=habit, date=checkin_date)


@pytest.mark.django_db
def test_checkin_model_save_does_not_call_clean(habit, monkeypatch):
    """Model save() must not call clean(), avoiding overhead on fixtures/bulk ops."""
    clean_called = False

    def mock_clean():
        nonlocal clean_called
        clean_called = True

    checkin = HabitCheckIn(habit=habit, date=date.today())
    monkeypatch.setattr(checkin, "clean", mock_clean)
    checkin.save()
    assert not clean_called, "HabitCheckIn.save() should not call clean()"


@pytest.mark.django_db
def test_checkin_model_allows_future_date_for_fixtures_and_bulk(habit):
    """Model clean() and save() do not reject future dates, leaving that to the service."""
    future_date = date.today() + timedelta(days=1)
    checkin = HabitCheckIn.objects.create(habit=habit, date=future_date)
    assert checkin.id is not None
    checkin.full_clean()  # Should not raise


@pytest.mark.django_db
def test_cascade_delete_habit_deletes_checkins(habit):
    HabitCheckIn.objects.create(habit=habit, date=date.today())
    assert HabitCheckIn.objects.filter(habit=habit).count() == 1
    habit.delete()
    assert HabitCheckIn.objects.filter(habit_id=habit.id).count() == 0


@pytest.mark.django_db
def test_habit_requires_user():
    with pytest.raises(IntegrityError):
        Habit.objects.create(name="No User Habit", color="#3B82F6", emoji="🎯")


@pytest.mark.django_db
def test_habit_belongs_to_user(user):
    habit = Habit.objects.create(user=user, name="User Habit", color="#3B82F6", emoji="🎯")
    assert habit.user == user
    assert habit in user.habits.all()


@pytest.mark.django_db
def test_delete_user_cascades_to_habits(user):
    Habit.objects.create(user=user, name="Habit 1")
    Habit.objects.create(user=user, name="Habit 2")
    assert user.habits.count() == 2
    user_id = user.id
    user.delete()
    assert Habit.objects.filter(user_id=user_id).count() == 0


def test_admin_registration():
    assert Habit in admin.site._registry
    assert HabitCheckIn in admin.site._registry


def test_habit_model_validation_rejects_invalid_color():
    habit = Habit(name="Test", color="invalid-hex")
    with pytest.raises(ValidationError):
        habit.full_clean()


def test_habit_model_validation_rejects_invalid_emoji():
    habit = Habit(name="Test", emoji="💧💧")
    with pytest.raises(ValidationError):
        habit.full_clean()


@pytest.mark.django_db
def test_habit_model_validation_accepts_valid_complex_emojis(user):
    for emoji in ["👍🏽", "🇺🇦", "❤️", "👨👩👧", "👨‍👩‍👧"]:
        habit = Habit(user=user, name="Test", emoji=emoji)
        habit.full_clean()  # Should not raise


@pytest.mark.django_db
def test_habit_default_frequency(user):
    habit = Habit.objects.create(user=user, name="Daily Habit")
    assert habit.frequency_type == "daily"
    assert habit.frequency_days == []
    assert habit.is_scheduled_on(date(2026, 10, 23))  # Friday
    assert habit.is_scheduled_on(date(2026, 10, 24))  # Saturday
    assert habit.is_scheduled_today() is True


@pytest.mark.django_db
def test_habit_custom_frequency_scheduling(user):
    # Mon (0), Wed (2), Fri (4)
    habit = Habit.objects.create(
        user=user,
        name="Gym",
        frequency_type="custom",
        frequency_days=[0, 2, 4],
    )
    assert habit.frequency_type == "custom"
    assert habit.frequency_days == [0, 2, 4]
    assert habit.is_scheduled_on(date(2026, 10, 23)) is True  # Friday is 4
    assert habit.is_scheduled_on(date(2026, 10, 24)) is False  # Saturday is 5
    assert habit.is_scheduled_on(date(2026, 10, 25)) is False  # Sunday is 6
    assert habit.is_scheduled_on(date(2026, 10, 26)) is True  # Monday is 0


@pytest.mark.django_db
def test_habit_validation_rejects_empty_frequency_days_for_custom(user):
    habit = Habit(user=user, name="Gym", frequency_type="custom", frequency_days=[])
    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()
    assert "frequency_days" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_days",
    [
        [-1],
        [7],
        [0, 7],
        ["mon"],
        [0, 1, 1],  # Duplicate
        [2, 3, 2],  # Duplicate
    ],
)
def test_habit_validation_rejects_invalid_frequency_days(user, invalid_days):
    habit = Habit(user=user, name="Gym", frequency_type="custom", frequency_days=invalid_days)
    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()
    assert "frequency_days" in exc_info.value.message_dict


@pytest.mark.django_db
def test_habit_validation_rejects_invalid_frequency_type(user):
    habit = Habit(user=user, name="Gym", frequency_type="yearly", frequency_days=[0])
    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()
    assert "frequency_type" in exc_info.value.message_dict


@pytest.mark.django_db
def test_habit_recalculates_streaks_on_frequency_change(user, monkeypatch):
    habit = Habit.objects.create(user=user, name="Gym")
    recalculate_called = False

    def mock_recalculate(h, reference_date=None):
        nonlocal recalculate_called
        recalculate_called = True
        return h

    monkeypatch.setattr("apps.habits.services.streaks.recalculate_habit_streaks", mock_recalculate)
    habit.frequency_type = "custom"
    habit.frequency_days = [0, 2, 4]
    habit.save()
    assert recalculate_called is True
