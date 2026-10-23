import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib import admin
from apps.habits.models import Habit, CheckIn, HabitCheckIn

@pytest.mark.django_db
def test_create_habit():
    habit = Habit.objects.create(
        name="Morning Jog",
        description="Jog for 30 minutes",
        color="#10B981",
        emoji="🏃"
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
    checkin = CheckIn.objects.create(habit=habit, date=checkin_date)
    assert checkin.id is not None
    assert checkin.habit == habit
    assert checkin.date == checkin_date
    assert checkin.created_at is not None
    assert f"{habit.name} - {checkin_date}" in str(checkin)


@pytest.mark.django_db
def test_unique_checkin_per_date_constraint(habit):
    checkin_date = date.today()
    CheckIn.objects.create(habit=habit, date=checkin_date)
    with pytest.raises(IntegrityError):
        CheckIn.objects.create(habit=habit, date=checkin_date)


@pytest.mark.django_db
def test_cannot_create_future_checkin_validation(habit):
    future_date = date.today() + timedelta(days=1)
    checkin = CheckIn(habit=habit, date=future_date)
    with pytest.raises(ValidationError):
        checkin.full_clean()


@pytest.mark.django_db
def test_cascade_delete_habit_deletes_checkins(habit):
    CheckIn.objects.create(habit=habit, date=date.today())
    assert CheckIn.objects.filter(habit=habit).count() == 1
    habit.delete()
    assert CheckIn.objects.filter(habit_id=habit.id).count() == 0


def test_admin_registration():
    assert Habit in admin.site._registry
    assert HabitCheckIn in admin.site._registry
