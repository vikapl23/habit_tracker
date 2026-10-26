from __future__ import annotations

import datetime
import logging
import zoneinfo
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from apps.habits.models import HabitCheckIn
from apps.habits.services.completion import is_day_completed
from apps.habits.services.statistics import (
    _calculate_range_completion,
    _get_habit_creation_date,
)
from apps.notifications.models import NotificationLog
from apps.notifications.tokens import build_unsubscribe_url

if TYPE_CHECKING:
    from apps.accounts.models import User

logger = logging.getLogger(__name__)

User = get_user_model()


def is_reminder_time_in_window(reminder_time: datetime.time, current_time: datetime.time) -> bool:
    """
    Determine if reminder_time falls in the current 15-minute window of current_time.
    Divides each hour into 4 15-minute buckets: [0, 15), [15, 30), [30, 45), [45, 60).
    """
    return reminder_time.hour == current_time.hour and (reminder_time.minute // 15) == (
        current_time.minute // 15
    )


def send_daily_reminder(user: User, user_today: datetime.date) -> bool:
    """
    Check if user has incomplete habits scheduled for user_today.
    Sends daily reminder email if any exist, and records in NotificationLog.
    Returns True if an email was sent, False otherwise.
    """
    if NotificationLog.objects.filter(
        user=user,
        notification_type=NotificationLog.NotificationType.DAILY_REMINDER,
        scheduled_date=user_today,
    ).exists():
        return False

    active_habits = user.habits.filter(is_archived=False)
    if not active_habits.exists():
        return False

    # Single query to prefetch today's check-ins for active habits
    today_checkins = {
        checkin.habit_id: checkin
        for checkin in HabitCheckIn.objects.filter(
            habit__in=active_habits,
            date=user_today,
        )
    }

    incomplete_items: list[dict[str, Any]] = []
    for habit in active_habits:
        if not habit.is_scheduled_on(user_today):
            continue

        checkin = today_checkins.get(habit.id)
        if not is_day_completed(habit, checkin):
            val = checkin.value if checkin else Decimal("0.00")
            incomplete_items.append({"habit": habit, "current_value": val})

    if not incomplete_items:
        return False

    unsubscribe_url = build_unsubscribe_url(user)
    context = {
        "user": user,
        "incomplete_habits": incomplete_items,
        "today": user_today,
        "unsubscribe_url": unsubscribe_url,
    }

    subject = f"Habit Reminder: You have {len(incomplete_items)} habit{'s' if len(incomplete_items) > 1 else ''} left today!"
    text_content = render_to_string("notifications/daily_reminder.txt", context)
    html_content = render_to_string("notifications/daily_reminder.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Habit Tracker <noreply@example.com>"),
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    NotificationLog.objects.create(
        user=user,
        notification_type=NotificationLog.NotificationType.DAILY_REMINDER,
        scheduled_date=user_today,
        recipient_email=user.email,
        details={
            "incomplete_habits_count": len(incomplete_items),
            "habit_ids": [item["habit"].id for item in incomplete_items],
        },
    )
    return True


def send_weekly_summary(user: User, user_today: datetime.date) -> bool:
    """
    Computes last week's completion %, best habit, and streaks.
    Sends weekly summary email and records in NotificationLog.
    Returns True if an email was sent, False otherwise.
    """
    start_of_current_week = user_today - datetime.timedelta(days=user_today.weekday())
    if NotificationLog.objects.filter(
        user=user,
        notification_type=NotificationLog.NotificationType.WEEKLY_SUMMARY,
        scheduled_date=start_of_current_week,
    ).exists():
        return False

    active_habits = list(user.habits.filter(is_archived=False).order_by("id"))
    if not active_habits:
        return False

    # Last week spans from last Monday to last Sunday
    last_week_start = start_of_current_week - datetime.timedelta(days=7)
    last_week_end = start_of_current_week - datetime.timedelta(days=1)

    # Fetch last week's check-ins in a single query
    checkins_data = HabitCheckIn.objects.filter(
        habit__in=active_habits,
        date__gte=last_week_start,
        date__lte=last_week_end,
    ).values_list("habit_id", "date", "value")

    checkin_map: dict[int, dict[datetime.date, Any]] = {h.id: {} for h in active_habits}
    for hid, d, val in checkins_data:
        checkin_map[hid][d] = val

    total_sched = 0
    total_comp = 0
    best_habit_data: dict[str, Any] | None = None
    best_rate = -1.0
    streaks: list[dict[str, Any]] = []

    for habit in active_habits:
        created_date = _get_habit_creation_date(habit, user)
        comp, sched, rate = _calculate_range_completion(
            habit,
            last_week_start,
            last_week_end,
            checkin_map.get(habit.id, {}),
            created_date,
        )
        total_comp += comp
        total_sched += sched

        if rate > best_rate and sched > 0:
            best_rate = rate
            best_habit_data = {
                "name": habit.name,
                "emoji": habit.emoji,
                "rate_percent": round(rate * 100, 1),
            }

        streaks.append(
            {
                "name": habit.name,
                "emoji": habit.emoji,
                "current_streak": habit.get_current_streak(user_today),
                "longest_streak": habit.longest_streak,
            }
        )

    completion_percentage = round(total_comp / total_sched * 100, 1) if total_sched > 0 else 0.0

    unsubscribe_url = build_unsubscribe_url(user)
    context = {
        "user": user,
        "last_week_start": last_week_start,
        "last_week_end": last_week_end,
        "completion_percentage": completion_percentage,
        "best_habit": best_habit_data,
        "streaks": streaks,
        "unsubscribe_url": unsubscribe_url,
    }

    subject = "Your Weekly Habit Summary 📊"
    text_content = render_to_string("notifications/weekly_summary.txt", context)
    html_content = render_to_string("notifications/weekly_summary.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Habit Tracker <noreply@example.com>"),
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    NotificationLog.objects.create(
        user=user,
        notification_type=NotificationLog.NotificationType.WEEKLY_SUMMARY,
        scheduled_date=start_of_current_week,
        recipient_email=user.email,
        details={
            "completion_percentage": completion_percentage,
            "best_habit": best_habit_data,
        },
    )
    return True


def send_due_notifications(
    now: datetime.datetime | None = None,
    force: bool = False,
) -> dict[str, int]:
    """
    Main dispatch service:
    1. Finds users whose local reminder time matches current 15-minute window (or all if force=True).
    2. Sends daily reminders and/or weekly summaries (on Mondays).
    3. Prevents duplicate deliveries using NotificationLog.
    Returns counts of sent notifications.
    """
    if now is None:
        now = timezone.now()

    daily_sent_count = 0
    weekly_sent_count = 0

    users = User.objects.filter(Q(daily_reminder_enabled=True) | Q(weekly_summary_enabled=True))

    for user in users:
        try:
            tz = zoneinfo.ZoneInfo(user.timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        user_now = now.astimezone(tz)
        user_time = user_now.time()
        user_today = user_now.date()

        reminder_time = user.daily_reminder_time or datetime.time(20, 0)
        time_matches = force or is_reminder_time_in_window(reminder_time, user_time)

        # 1. Daily Reminder
        if user.daily_reminder_enabled and time_matches:
            try:
                if send_daily_reminder(user, user_today):
                    daily_sent_count += 1
            except Exception as e:
                logger.exception(f"Failed to send daily reminder to {user.email}: {e}")

        # 2. Weekly Summary (Monday or force)
        is_monday = user_today.weekday() == 0
        weekly_due = (is_monday and time_matches) or force
        if user.weekly_summary_enabled and weekly_due:
            try:
                if send_weekly_summary(user, user_today):
                    weekly_sent_count += 1
            except Exception as e:
                logger.exception(f"Failed to send weekly summary to {user.email}: {e}")

    return {
        "daily_reminders_sent": daily_sent_count,
        "weekly_summaries_sent": weekly_sent_count,
        "total_sent": daily_sent_count + weekly_sent_count,
    }
