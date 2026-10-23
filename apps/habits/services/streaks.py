from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import NamedTuple

from django.utils import timezone


class StreakResult(NamedTuple):
    current_streak: int
    longest_streak: int


def calculate_streaks(
    checkin_dates: Iterable[date],
    reference_date: date | None = None,
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
        cursor = today
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
    habit,
    reference_date: date | None = None,
) -> StreakResult:
    """
    Convenience helper calculating streaks directly for a Habit model instance.
    Uses prefetched check_ins if available, otherwise queries values_list('date', flat=True).
    """
    if (
        hasattr(habit, "_prefetched_objects_cache")
        and "check_ins" in habit._prefetched_objects_cache
    ):
        dates = [ci.date for ci in habit.check_ins.all()]
    else:
        dates = list(habit.check_ins.values_list("date", flat=True))

    return calculate_streaks(dates, reference_date=reference_date)
