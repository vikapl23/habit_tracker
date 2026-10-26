from __future__ import annotations

from typing import Any

from apps.habits.models import Habit
from apps.habits.services.streaks import recalculate_habit_streaks


def update_habit(habit: Habit, **fields: Any) -> Habit:
    """
    Update habit attributes and trigger recalculate_habit_streaks in the service layer
    if frequency, habit_type, or target_value changed.
    """
    old_freq_type = habit.frequency_type
    old_freq_days = habit.frequency_days
    old_type = habit.habit_type
    old_target = habit.target_value

    for key, value in fields.items():
        setattr(habit, key, value)

    habit.save()

    if (
        old_freq_type != habit.frequency_type
        or old_freq_days != habit.frequency_days
        or old_type != habit.habit_type
        or old_target != habit.target_value
    ):
        recalculate_habit_streaks(habit)

    return habit
