from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, NamedTuple

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.habits.models import Habit, HabitCheckIn, suppress_streak_signals
from apps.habits.services.completion import is_day_completed
from apps.habits.services.streaks import recalculate_habit_streaks

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    from apps.accounts.models import User


class CheckInResult(NamedTuple):
    """Result data structure returned by check-in and uncheck operations."""

    status: str
    habit_id: int
    date: date
    current_streak: int
    longest_streak: int
    created: bool = False
    today_value: Decimal = Decimal("0.00")
    today_progress: float = 0.0
    is_completed: bool = False


def validate_checkin_date(
    target_date: date,
    user: User | AbstractBaseUser | AnonymousUser | None = None,
    habit: Habit | None = None,
) -> date:
    """Validate that target_date is not in the future relative to the user's timezone."""
    if user is None and habit is not None:
        user = getattr(habit, "user", None)

    max_date = user.get_today() if (user and hasattr(user, "get_today")) else timezone.localdate()
    if target_date > max_date:
        raise ValidationError({"date": "Check-ins cannot be recorded for future dates."})
    return target_date


def check_in_habit(
    habit: Habit,
    target_date: date | None = None,
    value: Decimal | float | int | None = None,
    mode: str = "add",
    user: User | AbstractBaseUser | AnonymousUser | None = None,
) -> CheckInResult:
    """
    Record or update a check-in for a habit on target_date.

    Modes:
    - 'add': adds value to existing day's total (defaults to 1 for measurable if None).
             Atomic in DB with select_for_update.
    - 'set': sets exact value. If value <= 0, deletes check-in.
    """
    if habit.is_archived:
        raise ValidationError({"detail": "Cannot check in on an archived habit."})

    if habit.habit_type == "boolean":
        if value is not None:
            raise ValidationError({"value": "Value is not allowed for boolean habits."})
        if mode != "add":
            raise ValidationError({"mode": "Custom modes are not supported for boolean habits."})

    if value is not None:
        try:
            dec_value = Decimal(str(value))
        except Exception as err:
            raise ValidationError({"value": "Invalid numeric value."}) from err
        if dec_value < Decimal("0"):
            raise ValidationError({"value": "Value cannot be negative."})
        if dec_value > Decimal("100000.00"):
            raise ValidationError({"value": "Value cannot exceed 100,000."})
    else:
        dec_value = Decimal("1.00") if habit.habit_type == "measurable" else Decimal("1.00")

    if user is None:
        user = getattr(habit, "user", None)

    today = user.get_today() if (user and hasattr(user, "get_today")) else timezone.localdate()
    target_date = target_date or today
    validate_checkin_date(target_date, user=user, habit=habit)

    created = False
    new_value = Decimal("0.00")
    status_str = "checked"

    with suppress_streak_signals():
        with transaction.atomic():
            checkin = (
                HabitCheckIn.objects.select_for_update()
                .filter(habit=habit, date=target_date)
                .first()
            )

            if habit.habit_type == "boolean":
                if not checkin:
                    checkin = HabitCheckIn.objects.create(
                        habit=habit, date=target_date, value=Decimal("1.00")
                    )
                    created = True
                new_value = Decimal("1.00")
            else:
                # Measurable habit
                if mode == "set":
                    if dec_value <= Decimal("0"):
                        if checkin:
                            checkin.delete()
                        new_value = Decimal("0.00")
                        status_str = "unchecked"
                    else:
                        if checkin:
                            checkin.value = dec_value
                            checkin.save(update_fields=["value"])
                        else:
                            checkin = HabitCheckIn.objects.create(
                                habit=habit, date=target_date, value=dec_value
                            )
                            created = True
                        new_value = dec_value
                else:
                    # mode == 'add'
                    if checkin:
                        new_value = checkin.value + dec_value
                        if new_value > Decimal("100000.00"):
                            raise ValidationError({"value": "Daily total cannot exceed 100,000."})
                        checkin.value = new_value
                        checkin.save(update_fields=["value"])
                    else:
                        new_value = dec_value
                        if new_value > Decimal("100000.00"):
                            raise ValidationError({"value": "Daily total cannot exceed 100,000."})
                        checkin = HabitCheckIn.objects.create(
                            habit=habit, date=target_date, value=new_value
                        )
                        created = True

    # Evict prefetched check_ins cache on the instance if present
    if hasattr(habit, "_prefetched_objects_cache"):
        habit._prefetched_objects_cache.pop("check_ins", None)

    recalculate_habit_streaks(habit, reference_date=today)

    # Calculate completion and progress
    target = habit.target_value or Decimal("1.00")
    is_completed = is_day_completed(habit, new_value) if status_str == "checked" else False
    if habit.habit_type == "boolean":
        progress = 100.0 if status_str == "checked" else 0.0
    else:
        progress = min(100.0, float(round((new_value / target) * 100, 1))) if target > 0 else 0.0

    return CheckInResult(
        status=status_str,
        habit_id=habit.id,
        date=target_date,
        current_streak=habit.get_current_streak(reference_date=today),
        longest_streak=habit.longest_streak,
        created=created,
        today_value=new_value,
        today_progress=progress,
        is_completed=is_completed,
    )


def uncheck_habit(
    habit: Habit,
    target_date: date | None = None,
    value: Decimal | float | int | None = None,
    user: User | AbstractBaseUser | AnonymousUser | None = None,
) -> CheckInResult:
    """
    Remove or decrement a check-in for a habit on target_date.
    - If measurable and value is provided: decrements the day's total. If <= 0, deletes.
    - If value is None (or boolean habit): deletes the check-in (explicit reset).
    """
    if user is None:
        user = getattr(habit, "user", None)

    today = user.get_today() if (user and hasattr(user, "get_today")) else timezone.localdate()
    target_date = target_date or today

    with suppress_streak_signals():
        with transaction.atomic():
            checkin = (
                HabitCheckIn.objects.select_for_update()
                .filter(habit=habit, date=target_date)
                .first()
            )
            if not checkin:
                raise NotFound(f"No check-in found for habit {habit.id} on {target_date}.")

            if habit.habit_type == "measurable" and value is not None:
                dec_val = Decimal(str(value))
                if dec_val < Decimal("0"):
                    raise ValidationError({"value": "Decrement value cannot be negative."})
                new_val = checkin.value - dec_val
                if new_val <= Decimal("0"):
                    checkin.delete()
                    final_val = Decimal("0.00")
                    status_str = "unchecked"
                else:
                    checkin.value = new_val
                    checkin.save(update_fields=["value"])
                    final_val = new_val
                    status_str = "checked"
            else:
                checkin.delete()
                final_val = Decimal("0.00")
                status_str = "unchecked"

    # Evict prefetched check_ins cache on the instance if present
    if hasattr(habit, "_prefetched_objects_cache"):
        habit._prefetched_objects_cache.pop("check_ins", None)

    recalculate_habit_streaks(habit, reference_date=today)

    target = habit.target_value or Decimal("1.00")
    is_completed = is_day_completed(habit, final_val) if status_str == "checked" else False
    if habit.habit_type == "boolean":
        progress = 100.0 if status_str == "checked" else 0.0
    else:
        progress = min(100.0, float(round((final_val / target) * 100, 1))) if target > 0 else 0.0

    return CheckInResult(
        status=status_str,
        habit_id=habit.id,
        date=target_date,
        current_streak=habit.get_current_streak(reference_date=today),
        longest_streak=habit.longest_streak,
        created=False,
        today_value=final_val,
        today_progress=progress,
        is_completed=is_completed,
    )
