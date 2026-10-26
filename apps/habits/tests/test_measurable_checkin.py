from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.habits.models import Habit, HabitCheckIn
from apps.habits.services import check_in_habit, uncheck_habit


@pytest.mark.django_db
def test_check_in_measurable_habit_accumulates(user):
    today = user.get_today()
    habit = Habit.objects.create(
        user=user,
        name="Water",
        habit_type="measurable",
        unit="glasses",
        target_value=Decimal("8.00"),
    )

    # First check-in: +2 glasses
    res1 = check_in_habit(
        habit=habit, target_date=today, value=Decimal("2.00"), mode="add", user=user
    )
    assert res1.today_value == Decimal("2.00")
    assert res1.today_progress == 25.0
    assert not res1.is_completed

    # Second check-in: +3 glasses -> total 5
    res2 = check_in_habit(
        habit=habit, target_date=today, value=Decimal("3.00"), mode="add", user=user
    )
    assert res2.today_value == Decimal("5.00")
    assert res2.today_progress == 62.5
    assert not res2.is_completed
    assert res2.current_streak == 0

    # Third check-in: +3 glasses -> total 8 -> completed!
    res3 = check_in_habit(
        habit=habit, target_date=today, value=Decimal("3.00"), mode="add", user=user
    )
    assert res3.today_value == Decimal("8.00")
    assert res3.today_progress == 100.0
    assert res3.is_completed
    assert res3.current_streak == 1


@pytest.mark.django_db
def test_check_in_measurable_habit_default_value_is_one(user):
    today = user.get_today()
    habit = Habit.objects.create(
        user=user,
        name="Pushups",
        habit_type="measurable",
        unit="times",
        target_value=Decimal("5.00"),
    )
    # Check in without value adds 1
    res = check_in_habit(habit=habit, target_date=today, user=user)
    assert res.today_value == Decimal("1.00")


@pytest.mark.django_db
def test_check_in_measurable_mode_set(user):
    today = user.get_today()
    habit = Habit.objects.create(
        user=user,
        name="Run",
        habit_type="measurable",
        unit="km",
        target_value=Decimal("5.00"),
    )
    # Set exact 4.5
    res = check_in_habit(
        habit=habit, target_date=today, value=Decimal("4.50"), mode="set", user=user
    )
    assert res.today_value == Decimal("4.50")

    # Set 0 removes check-in
    res2 = check_in_habit(
        habit=habit, target_date=today, value=Decimal("0.00"), mode="set", user=user
    )
    assert res2.today_value == Decimal("0.00")
    assert res2.status == "unchecked"


@pytest.mark.django_db
def test_uncheck_measurable_habit_decrements_and_resets(user):
    today = user.get_today()
    habit = Habit.objects.create(
        user=user,
        name="Water",
        habit_type="measurable",
        unit="glasses",
        target_value=Decimal("8.00"),
    )
    check_in_habit(habit=habit, target_date=today, value=Decimal("5.00"), mode="set", user=user)

    # Decrement by 2 -> 3
    res = uncheck_habit(habit=habit, target_date=today, value=Decimal("2.00"), user=user)
    assert res.today_value == Decimal("3.00")
    assert res.status == "checked"

    # Decrement without value -> resets day
    res2 = uncheck_habit(habit=habit, target_date=today, user=user)
    assert res2.today_value == Decimal("0.00")
    assert res2.status == "unchecked"


@pytest.mark.django_db
def test_boolean_habit_rejects_value(user):
    today = user.get_today()
    habit = Habit.objects.create(user=user, name="Meditation", habit_type="boolean")

    with pytest.raises(ValidationError):
        check_in_habit(habit=habit, target_date=today, value=Decimal("2.00"), user=user)


@pytest.mark.django_db
def test_atomic_concurrent_checkin_increments(user):
    """
    Simulate concurrent/fast repeated check-ins on the same day.
    All increments must add up atomically without lost updates.
    """
    today = user.get_today()
    habit = Habit.objects.create(
        user=user,
        name="Water",
        habit_type="measurable",
        unit="glasses",
        target_value=Decimal("20.00"),
    )

    # Fast sequential calls using atomic transaction select_for_update
    for _ in range(10):
        check_in_habit(habit=habit, target_date=today, value=Decimal("1.50"), mode="add", user=user)

    checkin = habit.check_ins.get(date=today)
    assert checkin.value == Decimal("15.00")


@pytest.mark.django_db
def test_check_in_concurrent_initial_creation_integrity_error_handled(user):
    """
    Test race condition on initial check-in creation where two requests both find checkin=None
    and attempt HabitCheckIn.objects.create(), one raising IntegrityError.
    The service must handle IntegrityError and accumulate/set value correctly.
    """
    from unittest.mock import patch
    from django.db import IntegrityError

    today = user.get_today()
    habit = Habit.objects.create(
        user=user,
        name="Water",
        habit_type="measurable",
        unit="glasses",
        target_value=Decimal("8.00"),
    )

    # Pre-create the check-in in the database simulating a concurrent request that committed first
    HabitCheckIn.objects.create(habit=habit, date=today, value=Decimal("3.00"))

    # When the current request queries first(), simulate that it saw None (race condition),
    # then calls create() which triggers IntegrityError because the row was already inserted.
    orig_filter = HabitCheckIn.objects.filter
    filter_calls = 0

    def mock_filter(*args, **kwargs):
        nonlocal filter_calls
        filter_calls += 1
        qs = orig_filter(*args, **kwargs)
        if filter_calls == 1:
            return qs.none()
        return qs

    def mock_create(*args, **kwargs):
        raise IntegrityError("unique constraint failed: unique_habit_checkin_per_date")

    with patch.object(HabitCheckIn.objects, "filter", side_effect=mock_filter):
        with patch("apps.habits.services.checkin.HabitCheckIn.objects.create", side_effect=mock_create):
            # Checking in 3 glasses in 'add' mode should fallback to updating existing 3 -> total 6 glasses
            res = check_in_habit(habit=habit, target_date=today, value=Decimal("3.00"), mode="add", user=user)
            assert res.today_value == Decimal("6.00")
            assert res.status == "checked"
