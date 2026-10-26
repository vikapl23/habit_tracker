from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from freezegun import freeze_time

from apps.habits.models import Habit, HabitCheckIn
from apps.notifications.models import NotificationLog
from apps.notifications.services import is_reminder_time_in_window, send_due_notifications

User = get_user_model()


@pytest.mark.django_db
class TestNotificationServices:
    def test_is_reminder_time_in_window(self):
        # 20:00 belongs to [20:00, 20:15)
        reminder = datetime.time(20, 0)
        assert is_reminder_time_in_window(reminder, datetime.time(20, 0)) is True
        assert is_reminder_time_in_window(reminder, datetime.time(20, 5)) is True
        assert is_reminder_time_in_window(reminder, datetime.time(20, 14, 59)) is True
        assert is_reminder_time_in_window(reminder, datetime.time(20, 15)) is False
        assert is_reminder_time_in_window(reminder, datetime.time(19, 59)) is False

    @freeze_time("2026-10-26 18:00:00")  # Monday, 18:00 UTC
    def test_timezone_window_dispatch(self):
        # 18:00 UTC is:
        # - 20:00 in Europe/Kyiv (UTC+2 in winter) -> MATCHES 20:00
        # - 14:00 in America/New_York (EDT UTC-4) -> DOES NOT MATCH 20:00
        user_kyiv = User.objects.create_user(
            email="kyiv@example.com",
            password="Password123!",
            timezone="Europe/Kyiv",
            daily_reminder_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        Habit.objects.create(user=user_kyiv, name="Kyiv Habit", habit_type="boolean")

        user_ny = User.objects.create_user(
            email="ny@example.com",
            password="Password123!",
            timezone="America/New_York",
            daily_reminder_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        Habit.objects.create(user=user_ny, name="NY Habit", habit_type="boolean")

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["kyiv@example.com"]

    @freeze_time("2026-10-26 20:00:00")
    def test_daily_reminder_nothing_sent_when_all_habits_completed(self):
        # UTC user at 20:00 UTC
        user = User.objects.create_user(
            email="done@example.com",
            password="Password123!",
            timezone="UTC",
            daily_reminder_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        habit = Habit.objects.create(user=user, name="Read Book", habit_type="boolean")
        HabitCheckIn.objects.create(habit=habit, date=datetime.date(2026, 10, 26))

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 0
        assert not NotificationLog.objects.filter(user=user).exists()

    @freeze_time("2026-10-26 20:00:00")
    def test_daily_reminder_sent_for_incomplete_habits(self):
        user = User.objects.create_user(
            email="todo@example.com",
            password="Password123!",
            timezone="UTC",
            daily_reminder_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        # Habit 1: done
        h1 = Habit.objects.create(user=user, name="Meditate", habit_type="boolean")
        HabitCheckIn.objects.create(habit=h1, date=datetime.date(2026, 10, 26))

        # Habit 2: incomplete boolean
        Habit.objects.create(user=user, name="Drink Water", habit_type="boolean")

        # Habit 3: measurable partial (target 5, value 2)
        h3 = Habit.objects.create(
            user=user,
            name="Walk",
            habit_type="measurable",
            target_value=Decimal("5.00"),
            unit="km",
        )
        HabitCheckIn.objects.create(
            habit=h3, date=datetime.date(2026, 10, 26), value=Decimal("2.00")
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["todo@example.com"]
        assert "Drink Water" in email.body
        assert "Walk" in email.body
        assert "Meditate" not in email.body
        assert "unsubscribe" in email.body.lower()

        # Check HTML alternative
        assert len(email.alternatives) == 1
        html_content, mimetype = email.alternatives[0]
        assert mimetype == "text/html"
        assert "Drink Water" in html_content
        assert "unsubscribe" in html_content.lower()

        # Check NotificationLog
        log = NotificationLog.objects.get(user=user, notification_type="daily_reminder")
        assert log.scheduled_date == datetime.date(2026, 10, 26)

    @freeze_time("2026-10-26 20:00:00")
    def test_no_duplicate_emails_sent(self):
        user = User.objects.create_user(
            email="nodupe@example.com",
            password="Password123!",
            timezone="UTC",
            daily_reminder_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        Habit.objects.create(user=user, name="Exercise", habit_type="boolean")

        # First run: sends
        counts1 = send_due_notifications()
        assert counts1["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1

        # Second run: does NOT send duplicate
        counts2 = send_due_notifications()
        assert counts2["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 1

    @freeze_time("2026-10-26 20:00:00")  # 2026-10-26 is Monday
    def test_weekly_summary_on_monday(self):
        user = User.objects.create_user(
            email="weekly@example.com",
            password="Password123!",
            timezone="UTC",
            weekly_summary_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        h = Habit.objects.create(
            user=user,
            name="Coding",
            habit_type="boolean",
            current_streak=4,
            longest_streak=10,
        )
        # Add some checkins for last week (2026-10-19 to 2026-10-25)
        HabitCheckIn.objects.create(habit=h, date=datetime.date(2026, 10, 20))
        HabitCheckIn.objects.create(habit=h, date=datetime.date(2026, 10, 21))

        counts = send_due_notifications()
        assert counts["weekly_summaries_sent"] == 1
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["weekly@example.com"]
        assert "Weekly" in email.subject
        assert "Coding" in email.body
        assert "unsubscribe" in email.body.lower()

        log = NotificationLog.objects.get(user=user, notification_type="weekly_summary")
        assert log.scheduled_date == datetime.date(2026, 10, 26)

    @freeze_time("2026-10-27 20:00:00")  # Tuesday
    def test_weekly_summary_not_sent_on_tuesday_without_force(self):
        user = User.objects.create_user(
            email="weekly_tuesday@example.com",
            password="Password123!",
            timezone="UTC",
            weekly_summary_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        Habit.objects.create(user=user, name="Coding", habit_type="boolean")

        counts = send_due_notifications()
        assert counts["weekly_summaries_sent"] == 0
        assert len(mail.outbox) == 0

    @freeze_time("2026-10-27 10:00:00")  # Tuesday morning, wrong time
    def test_force_flag_bypasses_time_window_and_day_check(self):
        user = User.objects.create_user(
            email="force@example.com",
            password="Password123!",
            timezone="UTC",
            daily_reminder_enabled=True,
            weekly_summary_enabled=True,
            daily_reminder_time=datetime.time(20, 0),
        )
        Habit.objects.create(user=user, name="Coding", habit_type="boolean")

        counts = send_due_notifications(force=True)
        assert counts["daily_reminders_sent"] == 1
        assert counts["weekly_summaries_sent"] == 1
        assert len(mail.outbox) == 2
