from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.habits.models import Habit, HabitCheckIn


def is_day_completed(
    habit: Habit,
    checkin_or_value: HabitCheckIn | Decimal | float | int | None = None,
) -> bool:
    """
    Determine if a habit is considered completed on a given day.
    ONE shared helper used everywhere: streaks, is_checked_today, today_progress,
    statistics (completion rates), calendar.

    Rules:
    - If checkin_or_value is None: Not completed (0 / no check-in).
    - If habit.habit_type == "boolean":
      - Completed if check-in exists (or True / checkin instance provided).
    - If habit.habit_type == "measurable":
      - If checkin_or_value is a HabitCheckIn instance, uses checkin_or_value.value.
      - Completed if and only if actual_value >= habit.target_value (where target_value > 0).
    """
    if checkin_or_value is None:
        return False

    habit_type = getattr(habit, "habit_type", "boolean")
    if habit_type == "boolean":
        return True

    # Measurable habit
    target = getattr(habit, "target_value", None)
    if target is None or target <= Decimal("0"):
        return False

    if hasattr(checkin_or_value, "value"):
        actual_val = checkin_or_value.value
    else:
        actual_val = checkin_or_value

    if actual_val is None:
        return False

    try:
        if not isinstance(actual_val, Decimal):
            actual_val = Decimal(str(actual_val))
        return actual_val >= target
    except Exception:
        return False
