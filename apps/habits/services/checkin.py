from __future__ import annotations

from datetime import date
from typing import NamedTuple

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.habits.models import Habit, HabitCheckIn
from apps.habits.services.streaks import recalculate_habit_streaks


class CheckInResult(NamedTuple):
    status: str
    habit_id: int
    date: date
    current_streak: int
    longest_streak: int
    created: bool = False


def validate_checkin_date(target_date: date, user=None, habit: Habit | None = None) -> date:
    """
    Validate that target_date is not in the future relative to the user's timezone.
    Single source of truth for future-date check-in validation.
    """
    if user is None and habit is not None:
        user = getattr(habit, "user", None)

    max_date = user.get_today() if (user and hasattr(user, "get_today")) else timezone.localdate()
    if target_date > max_date:
        raise ValidationError({"date": "Check-ins cannot be recorded for future dates."})
    return target_date


def check_in_habit(
    habit: Habit,
    target_date: date | None = None,
    user=None,
) -> CheckInResult:
    """
    Record a check-in for a habit on the given date (defaults to user's today).

    Race-safe: handles IntegrityError from concurrent inserts, returning the existing
    check-in instead of crashing with 500.

    Returns the updated habit state without modifying or relying on prefetched caches.
    """
    if habit.is_archived:
        raise ValidationError({"detail": "Cannot check in on an archived habit."})

    if user is None:
        user = getattr(habit, "user", None)

    today = user.get_today() if (user and hasattr(user, "get_today")) else timezone.localdate()
    target_date = target_date or today

    validate_checkin_date(target_date, user=user, habit=habit)

    created = False
    try:
        with transaction.atomic():
            _, created = HabitCheckIn.objects.get_or_create(habit=habit, date=target_date)
    except IntegrityError:
        try:
            HabitCheckIn.objects.get(habit=habit, date=target_date)
            created = False
        except HabitCheckIn.DoesNotExist:
            raise

    recalculate_habit_streaks(habit, reference_date=today)

    return CheckInResult(
        status="checked",
        habit_id=habit.id,
        date=target_date,
        current_streak=habit.get_current_streak(reference_date=today),
        longest_streak=habit.longest_streak,
        created=created,
    )


def uncheck_habit(
    habit: Habit,
    target_date: date | None = None,
    user=None,
) -> CheckInResult:
    """
    Remove a check-in for a habit on the given date (defaults to user's today).

    Returns the updated habit state without modifying or relying on prefetched caches.
    """
    if user is None:
        user = getattr(habit, "user", None)

    today = user.get_today() if (user and hasattr(user, "get_today")) else timezone.localdate()
    target_date = target_date or today

    checkin = HabitCheckIn.objects.filter(habit=habit, date=target_date).first()
    if not checkin:
        raise NotFound(f"No check-in found for habit {habit.id} on {target_date}.")

    checkin.delete()

    recalculate_habit_streaks(habit, reference_date=today)

    return CheckInResult(
        status="unchecked",
        habit_id=habit.id,
        date=target_date,
        current_streak=habit.get_current_streak(reference_date=today),
        longest_streak=habit.longest_streak,
        created=False,
    )
