from decimal import Decimal

import pytest

from apps.habits.models import Habit
from apps.habits.services.completion import is_day_completed


@pytest.mark.django_db
def test_is_day_completed_boolean_habit(user):
    habit = Habit.objects.create(user=user, name="Meditation", habit_type="boolean")
    assert not is_day_completed(habit, None)
    assert is_day_completed(habit, True)
    assert is_day_completed(habit, Decimal("1.00"))


@pytest.mark.django_db
def test_is_day_completed_measurable_habit(user):
    habit = Habit.objects.create(
        user=user,
        name="Water",
        habit_type="measurable",
        unit="glasses",
        target_value=Decimal("8.00"),
    )
    assert not is_day_completed(habit, None)
    assert not is_day_completed(habit, Decimal("0.00"))
    assert not is_day_completed(habit, Decimal("7.99"))
    assert is_day_completed(habit, Decimal("8.00"))
    assert is_day_completed(habit, Decimal("10.50"))
