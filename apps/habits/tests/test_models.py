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
