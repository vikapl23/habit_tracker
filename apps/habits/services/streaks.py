from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any, NamedTuple

from django.utils import timezone

if TYPE_CHECKING:
    from apps.habits.models import Habit


class StreakResult(NamedTuple):
    """Result data structure containing calculated streak counts."""

    current_streak: int
    longest_streak: int


def calculate_streaks(
    checkin_dates: Iterable[date | datetime | Any],
    reference_date: date | datetime | None = None,
) -> StreakResult:
    """
    Calculate current_streak and longest_streak for a collection of check-in dates.

    Rules:
    - current_streak: consecutive checked days ending today (reference_date).
      If today is not checked yet but yesterday is, the streak is still alive.
      If neither today nor yesterday is checked, current_streak is 0.
    - longest_streak: the longest consecutive run ever across all check-ins.
    """
    if reference_date is None:
        reference_date = timezone.localdate()
    elif isinstance(reference_date, datetime):
        reference_date = reference_date.date()

    raw_dates: set[date] = set()
    for item in checkin_dates:
        if isinstance(item, datetime):
            raw_dates.add(item.date())
        elif isinstance(item, date):
            raw_dates.add(item)
        elif hasattr(item, "date"):
            d = item.date() if callable(item.date) else item.date
            if isinstance(d, datetime):
                raw_dates.add(d.date())
            elif isinstance(d, date):
                raw_dates.add(d)

    valid_dates = {d for d in raw_dates if d <= reference_date}

    if not valid_dates:
        return StreakResult(current_streak=0, longest_streak=0)

    # 1. Current streak calculation
    today = reference_date
    yesterday = today - timedelta(days=1)

    if today in valid_dates:
        cursor: date | None = today
    elif yesterday in valid_dates:
        cursor = yesterday
    else:
        cursor = None

    current_streak = 0
    if cursor is not None:
        while cursor in valid_dates:
            current_streak += 1
            cursor -= timedelta(days=1)

    # 2. Longest streak calculation
    sorted_dates = sorted(valid_dates)
    longest_streak = 1
    curr_run = 1

    for i in range(1, len(sorted_dates)):
        diff = (sorted_dates[i] - sorted_dates[i - 1]).days
        if diff == 1:
            curr_run += 1
        elif diff == 0:
            continue
        else:
            curr_run = 1

        if curr_run > longest_streak:
            longest_streak = curr_run

    return StreakResult(current_streak=current_streak, longest_streak=longest_streak)


def calculate_habit_streaks(
    habit: Habit,
    reference_date: date | datetime | None = None,
) -> StreakResult:
    """
    Calculate streaks directly for a Habit model instance.

    Uses prefetched check_ins if available, otherwise queries values_list('date', flat=True).
    """
    if reference_date is None:
        user = getattr(habit, "user", None)
        if user and hasattr(user, "get_today"):
            reference_date = user.get_today()
        else:
            reference_date = timezone.localdate()

    if (
        hasattr(habit, "_prefetched_objects_cache")
        and "check_ins" in habit._prefetched_objects_cache
    ):
        dates: list[date] = [ci.date for ci in habit.check_ins.all()]
    else:
        dates = list(habit.check_ins.values_list("date", flat=True))

    return calculate_streaks(dates, reference_date=reference_date)


def recalculate_habit_streaks(
    habit: Habit,
    reference_date: date | datetime | None = None,
) -> Habit:
    """
    Recalculate current_streak, longest_streak, and last_check_in_date for a habit,
    and persist them to the database.
    """
    if reference_date is None:
        user = getattr(habit, "user", None)
        if user and hasattr(user, "get_today"):
            reference_date = user.get_today()
        else:
            reference_date = timezone.localdate()

    dates = list(habit.check_ins.values_list("date", flat=True))
    streaks = calculate_streaks(dates, reference_date=reference_date)
    last_date = max(dates) if dates else None

    habit.current_streak = streaks.current_streak
    habit.longest_streak = streaks.longest_streak
    habit.last_check_in_date = last_date
    habit.save(
        update_fields=["current_streak", "longest_streak", "last_check_in_date", "updated_at"]
    )
    return habit
