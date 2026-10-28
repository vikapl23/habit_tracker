from __future__ import annotations

import datetime
import logging
import zoneinfo
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.habits.models import Habit, HabitCheckIn
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


def format_amount(val: Any) -> str:
    """Format decimal/float without unnecessary trailing zeros (e.g. 3 instead of 3.00)."""
    if val is None:
        return "0"
    d = Decimal(str(val))
    if d == d.to_integral():
        return str(d.to_integral())
    return f"{d.normalize():f}"


def is_reminder_time_in_window(reminder_time: datetime.time, current_time: datetime.time) -> bool:
    """
    Determine if reminder_time falls in the current 15-minute window of current_time.
    Divides each hour into 4 15-minute buckets: [0, 15), [15, 30), [30, 45), [45, 60).
    """
    return reminder_time.hour == current_time.hour and (reminder_time.minute // 15) == (
        current_time.minute // 15
    )


def _send_habit_reminder_email(
    user: User,
    user_today: datetime.date,
    incomplete_items: list[dict[str, Any]],
) -> bool:
    """
    Render and send daily habit reminder email for a user, claiming NotificationLog
    records atomically before sending to prevent duplicates and releasing on failure.
    """
    if not incomplete_items:
        return False

    unsubscribe_url = build_unsubscribe_url(user)
    context = {
        "user": user,
        "incomplete_habits": incomplete_items,
        "today": user_today,
        "unsubscribe_url": unsubscribe_url,
    }

    count = len(incomplete_items)
    subject = f"Habit Reminder: You have {count} habit{'s' if count > 1 else ''} left today!"
    text_content = render_to_string("notifications/daily_reminder.txt", context)
    html_content = render_to_string("notifications/daily_reminder.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Habit Tracker <noreply@example.com>"),
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")

    # Claim notification logs inside a transaction before sending to prevent duplicate sends
    claimed_logs = [
        NotificationLog(
            user=user,
            habit=item["habit"],
            notification_type=NotificationLog.NotificationType.DAILY_REMINDER,
            scheduled_date=user_today,
            recipient_email=user.email,
            details={
                "habit_id": item["habit"].id,
                "habit_name": item["habit"].name,
                "current_value": str(item["current_value"]),
                "progress_text": item["progress_text"],
            },
        )
        for item in incomplete_items
    ]
    try:
        with transaction.atomic():
            NotificationLog.objects.bulk_create(claimed_logs)
    except IntegrityError:
        logger.warning(
            f"Habit reminders for user {user.pk} on {user_today} already claimed by another process."
        )
        return False

    try:
        msg.send()
    except Exception:
        # Release claimed log rows if sending fails so next run can retry
        NotificationLog.objects.filter(
            habit__in=[item["habit"] for item in incomplete_items],
            scheduled_date=user_today,
        ).delete()
        raise

    return True


def send_habit_reminders_for_user(
    user: User,
    user_today: datetime.date,
    user_time: datetime.time,
    force: bool = False,
) -> bool:
    """
    Find habits for user with reminder_enabled whose reminder_time falls in current 15-minute window,
    that are scheduled today and NOT completed (using shared completion helper).
    Groups all such habits into ONE email.
    Logs per habit per day in NotificationLog.
    Returns True if an email was sent, False otherwise.
    """
    candidate_habits = user.habits.filter(is_archived=False, reminder_enabled=True)
    if not candidate_habits.exists():
        return False

    due_habits: list[Any] = []
    for habit in candidate_habits:
        if not force:
            if not habit.reminder_time or habit.reminder_time > user_time:
                continue
        if not habit.is_scheduled_on(user_today):
            continue
        # Deduplication: each habit reminded at most once per day
        if NotificationLog.objects.filter(
            habit=habit,
            scheduled_date=user_today,
        ).exists():
            continue
        due_habits.append(habit)

    if not due_habits:
        return False

    # Prefetch today's check-ins for due habits
    today_checkins = {
        checkin.habit_id: checkin
        for checkin in HabitCheckIn.objects.filter(
            habit__in=due_habits,
            date=user_today,
        )
    }

    incomplete_items: list[dict[str, Any]] = []
    for habit in due_habits:
        checkin = today_checkins.get(habit.id)
        if not is_day_completed(habit, checkin):
            val = checkin.value if checkin else Decimal("0.00")
            progress_text = (
                f"{format_amount(val)} / {format_amount(habit.target_value)} {habit.unit}"
                if habit.habit_type == "measurable"
                else ""
            )
            incomplete_items.append(
                {
                    "habit": habit,
                    "current_value": val,
                    "progress_text": progress_text,
                }
            )

    return _send_habit_reminder_email(user, user_today, incomplete_items)


def send_daily_reminder(user: User, user_today: datetime.date) -> bool:
    """Convenience helper to force send due daily reminders for a user."""
    return send_habit_reminders_for_user(
        user=user,
        user_today=user_today,
        user_time=datetime.time(0, 0),
        force=True,
    )


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

    # Claim notification log inside a transaction before sending to prevent duplicate sends
    try:
        with transaction.atomic():
            claimed_log = NotificationLog.objects.create(
                user=user,
                habit=None,
                notification_type=NotificationLog.NotificationType.WEEKLY_SUMMARY,
                scheduled_date=start_of_current_week,
                recipient_email=user.email,
                details={
                    "completion_percentage": completion_percentage,
                    "best_habit": best_habit_data,
                },
            )
    except IntegrityError:
        logger.warning(
            f"Weekly summary for user {user.pk} on {start_of_current_week} already claimed."
        )
        return False

    try:
        msg.send()
    except Exception:
        # Release claimed log row if sending fails so next run can retry
        claimed_log.delete()
        raise

    return True


def send_due_notifications(
    now: datetime.datetime | None = None,
    force: bool = False,
) -> dict[str, int]:
    """
    Main dispatch service:
    1. For each user with notifications_enabled=True (respecting their timezone):
       - Finds habits with reminder_enabled whose reminder_time has passed today,
         that are scheduled today and NOT completed.
       - Bulk-queries candidate habits, logs, and check-ins to prevent N+1 queries.
       - Groups all such habits of one user into ONE email.
       - Atomically claims records in NotificationLog before sending.
       - No email if the list is empty.
    2. Sends weekly summaries on Monday (if weekly_summary_enabled=True).
    Returns counts of sent notifications.
    """
    if now is None:
        now = timezone.now()

    daily_sent_count = 0
    weekly_sent_count = 0

    # 1. Query candidate habits directly to avoid N+1 queries across users
    candidate_habits = Habit.objects.filter(
        reminder_enabled=True,
        is_archived=False,
        user__notifications_enabled=True,
    ).select_related("user")

    due_candidates: list[tuple[Any, Any, datetime.date]] = []
    candidate_dates: set[datetime.date] = set()

    for habit in candidate_habits:
        user = habit.user
        try:
            tz = zoneinfo.ZoneInfo(user.timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        user_now = now.astimezone(tz)
        user_time = user_now.time()
        user_today = user_now.date()

        if not force:
            if not habit.reminder_time or habit.reminder_time > user_time:
                continue
        if not habit.is_scheduled_on(user_today):
            continue

        due_candidates.append((habit, user, user_today))
        candidate_dates.add(user_today)

    if due_candidates:
        candidate_habit_ids = [h.id for h, _, _ in due_candidates]
        existing_logs = set(
            NotificationLog.objects.filter(
                habit_id__in=candidate_habit_ids,
                scheduled_date__in=candidate_dates,
            ).values_list("habit_id", "scheduled_date")
        )

        unlogged_candidates = [
            (h, u, d) for (h, u, d) in due_candidates if (h.id, d) not in existing_logs
        ]

        if unlogged_candidates:
            unlogged_habit_ids = [h.id for h, _, _ in unlogged_candidates]
            checkins = HabitCheckIn.objects.filter(
                habit_id__in=unlogged_habit_ids,
                date__in=candidate_dates,
            )
            checkin_map = {(c.habit_id, c.date): c for c in checkins}

            user_items_map: dict[tuple[int, datetime.date], tuple[Any, list[dict[str, Any]]]] = {}
            for h, u, d in unlogged_candidates:
                checkin = checkin_map.get((h.id, d))
                if not is_day_completed(h, checkin):
                    val = checkin.value if checkin else Decimal("0.00")
                    progress_text = (
                        f"{format_amount(val)} / {format_amount(h.target_value)} {h.unit}"
                        if h.habit_type == "measurable"
                        else ""
                    )
                    key = (u.id, d)
                    if key not in user_items_map:
                        user_items_map[key] = (u, [])
                    user_items_map[key][1].append(
                        {
                            "habit": h,
                            "current_value": val,
                            "progress_text": progress_text,
                        }
                    )

            for (_u_id, d), (u, items) in user_items_map.items():
                try:
                    if _send_habit_reminder_email(u, d, items):
                        daily_sent_count += 1
                except Exception as e:
                    logger.exception(f"Failed to send habit reminders to {u.email}: {e}")

    # 2. Weekly Summary (Monday or force)
    weekly_users = User.objects.filter(
        notifications_enabled=True,
        weekly_summary_enabled=True,
    )
    for user in weekly_users:
        try:
            tz = zoneinfo.ZoneInfo(user.timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        user_now = now.astimezone(tz)
        user_time = user_now.time()
        user_today = user_now.date()
        is_monday = user_today.weekday() == 0
        weekly_time_matches = force or user_time >= datetime.time(9, 0)
        if (is_monday and weekly_time_matches) or force:
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
