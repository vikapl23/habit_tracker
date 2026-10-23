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


def _is_scheduled_day(
    target_date: date,
    frequency_type: str = "daily",
    frequency_days: Iterable[int] | None = None,
) -> bool:
    """Return True if target_date is a scheduled day according to habit frequency."""
    if frequency_type == "daily":
        return True
    if frequency_type != "custom" or not frequency_days:
        return False
    return target_date.weekday() in frequency_days


def _find_prev_scheduled_day(
    from_date: date,
    frequency_type: str = "daily",
    frequency_days: Iterable[int] | None = None,
    max_lookback: int = 7,
) -> date | None:
    """Find the most recent scheduled day strictly prior to from_date within max_lookback days."""
    for i in range(1, max_lookback + 1):
        candidate = from_date - timedelta(days=i)
        if _is_scheduled_day(candidate, frequency_type, frequency_days):
            return candidate
    return None


def calculate_streaks(
    checkin_dates: Iterable[date | datetime | Any],
    reference_date: date | datetime | None = None,
    frequency_type: str = "daily",
    frequency_days: Iterable[int] | None = None,
) -> StreakResult:
    """
    Calculate current_streak and longest_streak for a collection of check-in dates,
    accounting for habit scheduling and frequency.

    Rules:
    - Only scheduled days count towards streaks.
    - Off-schedule days (e.g. weekends for weekday-only habits) never break a streak.
    - A check-in on an off-schedule day is ignored for streak calculations.
    - current_streak:
      - If today is scheduled and checked, streak includes today and consecutive prior scheduled days.
      - If today is scheduled but not checked yet, streak is still alive based on prior scheduled days.
      - If today is off-schedule, streak is alive based on prior scheduled days.
      - If a scheduled day was missed, current streak is 0.
    - longest_streak: the longest consecutive run across scheduled check-ins ever.
    """
    if reference_date is None:
        reference_date = timezone.localdate()
    elif isinstance(reference_date, datetime):
        reference_date = reference_date.date()

    if frequency_days is not None:
        frequency_days = set(frequency_days)

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

    # Filter to only scheduled days on or before reference_date
    scheduled_valid_dates = {
        d
        for d in raw_dates
        if d <= reference_date and _is_scheduled_day(d, frequency_type, frequency_days)
    }

    if frequency_type not in ("daily", "custom") or (
        frequency_type == "custom" and not frequency_days
    ):
        return StreakResult(current_streak=0, longest_streak=0)

    # 1. Current streak calculation
    cursor: date | None = None
    today = reference_date

    if _is_scheduled_day(today, frequency_type, frequency_days):
        if today in scheduled_valid_dates:
            cursor = today
        else:
            # Today is scheduled but not checked yet; streak stays alive if previous scheduled day is checked
            prev_scheduled = _find_prev_scheduled_day(today, frequency_type, frequency_days)
            if prev_scheduled and prev_scheduled in scheduled_valid_dates:
                cursor = prev_scheduled
    else:
        # Today is off-schedule; streak stays alive if most recent scheduled day was checked
        last_scheduled = _find_prev_scheduled_day(today, frequency_type, frequency_days)
        if last_scheduled and last_scheduled in scheduled_valid_dates:
            cursor = last_scheduled

    current_streak = 0
    if cursor is not None:
        while cursor in scheduled_valid_dates:
            current_streak += 1
            prev = _find_prev_scheduled_day(cursor, frequency_type, frequency_days)
            if prev is None:
                break
            cursor = prev

    # 2. Longest streak calculation
    if not scheduled_valid_dates:
        return StreakResult(current_streak=0, longest_streak=0)

    sorted_dates = sorted(scheduled_valid_dates)
    longest_streak = 1
    curr_run = 1

    for i in range(1, len(sorted_dates)):
        prev = sorted_dates[i - 1]
        curr = sorted_dates[i]

        has_missed_scheduled_day = False
        check_day = prev + timedelta(days=1)
        while check_day < curr:
            if _is_scheduled_day(check_day, frequency_type, frequency_days):
                has_missed_scheduled_day = True
                break
            check_day += timedelta(days=1)

        if not has_missed_scheduled_day:
            curr_run += 1
        else:
            curr_run = 1

        if curr_run > longest_streak:
            longest_streak = curr_run

    longest_streak = max(longest_streak, current_streak)
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

    return calculate_streaks(
        dates,
        reference_date=reference_date,
        frequency_type=habit.frequency_type,
        frequency_days=habit.frequency_days,
    )


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
    streaks = calculate_streaks(
        dates,
        reference_date=reference_date,
        frequency_type=habit.frequency_type,
        frequency_days=habit.frequency_days,
    )
    last_date = max(dates) if dates else None

    habit.current_streak = streaks.current_streak
    habit.longest_streak = streaks.longest_streak
    habit.last_check_in_date = last_date
    habit.save(
        update_fields=["current_streak", "longest_streak", "last_check_in_date", "updated_at"]
    )
    return habit
