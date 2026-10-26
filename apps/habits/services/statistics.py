from __future__ import annotations

import zoneinfo
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.habits.models import Habit, HabitCheckIn

if TYPE_CHECKING:
    from apps.accounts.models import User


def is_day_completed(
    target_date: date,
    checkin_dates: set[date],
    # Placeholder for future measurable habits with units/targets
    target_value: Any = None,
    actual_value: Any = None,
) -> bool:
    """
    Determine if a habit is considered completed on a given target_date.
    Centralized helper so measurable habits with units/targets can be integrated cleanly later.
    """
    return target_date in checkin_dates


def _get_user_today(user: User | None = None) -> date:
    """Return today's date in user's timezone if available, otherwise localdate."""
    if user and hasattr(user, "get_today"):
        return user.get_today()
    return timezone.localdate()


def _get_habit_creation_date(habit: Habit, user: User | None = None) -> date:
    """Return creation date of habit in user's timezone or UTC."""
    created_at = habit.created_at
    if not created_at:
        return _get_user_today(user)
    if user and getattr(user, "timezone", None):
        try:
            tz = zoneinfo.ZoneInfo(user.timezone)
            return created_at.astimezone(tz).date()
        except Exception:
            pass
    return created_at.date()


def _calculate_range_completion(
    habit: Habit,
    start_date: date,
    end_date: date,
    checkin_dates: set[date],
    habit_created_date: date,
) -> tuple[int, int, float]:
    """
    Calculate (completed_days, scheduled_days, rate) for a date range [start_date, end_date].
    Days before the habit was created do NOT count.
    """
    effective_start = max(start_date, habit_created_date)
    if effective_start > end_date:
        return 0, 0, 0.0

    scheduled_days = 0
    completed_days = 0

    curr = effective_start
    while curr <= end_date:
        if habit.is_scheduled_on(curr):
            scheduled_days += 1
            if is_day_completed(curr, checkin_dates):
                completed_days += 1
        curr += timedelta(days=1)

    rate = round(completed_days / scheduled_days, 4) if scheduled_days > 0 else 0.0
    return completed_days, scheduled_days, rate


def calculate_habit_statistics(
    habit: Habit,
    user: User | None = None,
    reference_date: date | None = None,
    checkins_cache: set[date] | None = None,
    total_checkins_cache: int | None = None,
) -> dict[str, Any]:
    """
    Calculate statistics for a single habit:
    - completion rate for the last 7 and 30 days
    - total check-ins
    - current and longest streak
    """
    if user is None:
        user = habit.user

    if reference_date is None:
        reference_date = _get_user_today(user)

    habit_created_date = _get_habit_creation_date(habit, user)

    # 7-day window: [reference_date - 6, reference_date]
    # 30-day window: [reference_date - 29, reference_date]
    window_7d_start = reference_date - timedelta(days=6)
    window_30d_start = reference_date - timedelta(days=29)

    if checkins_cache is not None:
        checkin_dates = checkins_cache
        total_check_ins = (
            total_checkins_cache if total_checkins_cache is not None else len(checkin_dates)
        )
    else:
        # Load check-in dates for this habit
        all_checkin_dates = set(habit.check_ins.values_list("date", flat=True))
        checkin_dates = all_checkin_dates
        total_check_ins = len(all_checkin_dates)

    _, _, rate_7d = _calculate_range_completion(
        habit, window_7d_start, reference_date, checkin_dates, habit_created_date
    )
    _, _, rate_30d = _calculate_range_completion(
        habit, window_30d_start, reference_date, checkin_dates, habit_created_date
    )

    current_streak = habit.get_current_streak(reference_date)
    longest_streak = habit.longest_streak

    return {
        "habit_id": habit.id,
        "completion_rate_7d": rate_7d,
        "completion_rate_30d": rate_30d,
        "total_check_ins": total_check_ins,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
    }


def calculate_user_summary_statistics(
    user: User,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """
    Calculate summary statistics for all active habits of a user:
    - overall completion rate this week (Monday to Sunday or Monday to reference_date)
    - overall completion rate this month (1st of month to reference_date or end of month)
    - best habit (highest 30-day completion rate)
    - total active habits
    - total check-ins across all user habits
    """
    if reference_date is None:
        reference_date = _get_user_today(user)

    # Active habits for this user
    active_habits = list(user.habits.filter(is_archived=False).order_by("id"))
    total_active_habits = len(active_habits)

    # Total check-ins across all user's habits (including archived or not? Requirement: "total check-ins")
    total_check_ins = HabitCheckIn.objects.filter(habit__user=user).count()

    if not active_habits:
        return {
            "overall_completion_rate_week": 0.0,
            "overall_completion_rate_month": 0.0,
            "best_habit": None,
            "total_active_habits": 0,
            "total_check_ins": total_check_ins,
        }

    # "this week": Monday of current week up to reference_date
    # weekday(): Monday is 0
    start_of_week = reference_date - timedelta(days=reference_date.weekday())
    # "this month": 1st day of current month up to reference_date
    start_of_month = reference_date.replace(day=1)

    earliest_date = min(start_of_week, start_of_month, reference_date - timedelta(days=29))

    # Fetch check-ins for active habits from earliest_date to reference_date in a SINGLE query
    active_habit_ids = [h.id for h in active_habits]
    relevant_checkins = HabitCheckIn.objects.filter(
        habit_id__in=active_habit_ids,
        date__gte=earliest_date,
        date__lte=reference_date,
    ).values_list("habit_id", "date")
    checkins_by_habit: dict[int, set[date]] = {hid: set() for hid in active_habit_ids}
    for hid, d in relevant_checkins:
        checkins_by_habit[hid].add(d)

    total_week_scheduled = 0
    total_week_completed = 0

    total_month_scheduled = 0
    total_month_completed = 0

    best_habit = None
    best_rate_30d = -1.0

    window_30d_start = reference_date - timedelta(days=29)

    for habit in active_habits:
        c_dates = checkins_by_habit.get(habit.id, set())
        created_date = _get_habit_creation_date(habit, user)

        # Week
        w_comp, w_sched, _ = _calculate_range_completion(
            habit, start_of_week, reference_date, c_dates, created_date
        )
        total_week_completed += w_comp
        total_week_scheduled += w_sched

        # Month
        m_comp, m_sched, _ = _calculate_range_completion(
            habit, start_of_month, reference_date, c_dates, created_date
        )
        total_month_completed += m_comp
        total_month_scheduled += m_sched

        # 30-day rate for best habit
        _, _, rate_30d = _calculate_range_completion(
            habit, window_30d_start, reference_date, c_dates, created_date
        )
        if rate_30d > best_rate_30d:
            best_rate_30d = rate_30d
            best_habit = {
                "id": habit.id,
                "name": habit.name,
                "emoji": habit.emoji,
                "color": habit.color,
                "completion_rate_30d": rate_30d,
            }

    overall_week_rate = (
        round(total_week_completed / total_week_scheduled, 4) if total_week_scheduled > 0 else 0.0
    )
    overall_month_rate = (
        round(total_month_completed / total_month_scheduled, 4)
        if total_month_scheduled > 0
        else 0.0
    )

    return {
        "overall_completion_rate_week": overall_week_rate,
        "overall_completion_rate_month": overall_month_rate,
        "best_habit": best_habit,
        "total_active_habits": total_active_habits,
        "total_check_ins": total_check_ins,
    }
