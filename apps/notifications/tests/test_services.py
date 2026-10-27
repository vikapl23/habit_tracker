from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from freezegun import freeze_time

from apps.habits.models import FrequencyType, Habit, HabitCheckIn
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

    @freeze_time("2026-10-26 09:00:00")  # Monday, 09:00 UTC
    def test_two_habits_with_different_times(self):
        user = User.objects.create_user(
            email="two_times@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        # Habit A: reminder at 09:00
        h_morning = Habit.objects.create(
            user=user,
            name="Morning Yoga",
            emoji="🧘",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )
        # Habit B: reminder at 14:00
        h_afternoon = Habit.objects.create(
            user=user,
            name="Afternoon Walk",
            emoji="🚶",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(14, 0),
        )

        # At 09:00: Only Habit A is due
        counts_morning = send_due_notifications()
        assert counts_morning["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        email_morning = mail.outbox[0]
        assert "Morning Yoga" in email_morning.body
        assert "Afternoon Walk" not in email_morning.body
        assert NotificationLog.objects.filter(habit=h_morning).exists()
        assert not NotificationLog.objects.filter(habit=h_afternoon).exists()

        mail.outbox.clear()

        # At 14:00: Habit B is due
        with freeze_time("2026-10-26 14:00:00"):
            counts_afternoon = send_due_notifications()
            assert counts_afternoon["daily_reminders_sent"] == 1
            assert len(mail.outbox) == 1
            email_afternoon = mail.outbox[0]
            assert "Afternoon Walk" in email_afternoon.body
            assert "Morning Yoga" not in email_afternoon.body
            assert NotificationLog.objects.filter(habit=h_afternoon).exists()

    @freeze_time("2026-10-26 09:00:00")
    def test_group_multiple_due_habits_into_one_email(self):
        user = User.objects.create_user(
            email="group@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        h1 = Habit.objects.create(
            user=user,
            name="Drink Water",
            emoji="💧",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )
        h2 = Habit.objects.create(
            user=user,
            name="Meditate",
            emoji="🧘",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["group@example.com"]
        assert "Drink Water" in email.body
        assert "Meditate" in email.body
        assert NotificationLog.objects.filter(habit=h1).count() == 1
        assert NotificationLog.objects.filter(habit=h2).count() == 1

    @freeze_time("2026-10-26 09:00:00")
    def test_habit_already_completed_no_email(self):
        user = User.objects.create_user(
            email="completed@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit = Habit.objects.create(
            user=user,
            name="Read Book",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )
        HabitCheckIn.objects.create(habit=habit, date=datetime.date(2026, 10, 26))

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 0
        assert not NotificationLog.objects.filter(habit=habit).exists()

    @freeze_time("2026-10-26 09:00:00")
    def test_measurable_partial_triggers_email_with_progress(self):
        user = User.objects.create_user(
            email="partial@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit = Habit.objects.create(
            user=user,
            name="Drink Water",
            emoji="💧",
            habit_type="measurable",
            target_value=Decimal("8.00"),
            unit="glasses",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )
        # Partially checked: 3 / 8 glasses
        HabitCheckIn.objects.create(
            habit=habit, date=datetime.date(2026, 10, 26), value=Decimal("3.00")
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert "Drink Water" in email.body
        assert "3 / 8 glasses" in email.body
        assert "unsubscribe" in email.body.lower()

        # Check HTML alternative
        assert len(email.alternatives) == 1
        html_content, mimetype = email.alternatives[0]
        assert mimetype == "text/html"
        assert "3 / 8 glasses" in html_content
        assert "unsubscribe" in html_content.lower()

    @freeze_time("2026-10-26 09:00:00")
    def test_measurable_completed_target_reached_no_email(self):
        user = User.objects.create_user(
            email="targetdone@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit = Habit.objects.create(
            user=user,
            name="Drink Water",
            habit_type="measurable",
            target_value=Decimal("8.00"),
            unit="glasses",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )
        # Fully completed: 8 / 8 glasses
        HabitCheckIn.objects.create(
            habit=habit, date=datetime.date(2026, 10, 26), value=Decimal("8.00")
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 0

    @freeze_time("2026-10-24 09:00:00")  # Saturday
    def test_off_schedule_day_no_email(self):
        user = User.objects.create_user(
            email="offschedule@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        # Habit scheduled Mon-Fri only [0, 1, 2, 3, 4]
        habit = Habit.objects.create(
            user=user,
            name="Work Coding",
            habit_type="boolean",
            frequency_type=FrequencyType.CUSTOM,
            frequency_days=[0, 1, 2, 3, 4],
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 0
        assert not NotificationLog.objects.filter(habit=habit).exists()

    @freeze_time("2026-10-26 09:00:00")
    def test_master_switch_off_no_email(self):
        user = User.objects.create_user(
            email="masteroff@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=False,  # Master switch OFF
        )
        Habit.objects.create(
            user=user,
            name="Jogging",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 0

    @freeze_time("2026-10-26 09:00:00")
    def test_no_duplicate_emails_per_habit_per_day(self):
        user = User.objects.create_user(
            email="nodupe@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        h = Habit.objects.create(
            user=user,
            name="Exercise",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        # First run: email sent
        counts1 = send_due_notifications()
        assert counts1["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        assert NotificationLog.objects.filter(habit=h).count() == 1

        # Second run 5 mins later in the same window: does NOT send duplicate
        with freeze_time("2026-10-26 09:05:00"):
            counts2 = send_due_notifications()
            assert counts2["daily_reminders_sent"] == 0
            assert len(mail.outbox) == 1

    @freeze_time("2026-10-26 07:00:00")  # Monday, 07:00 UTC
    def test_user_timezone_windows(self):
        # At 07:00 UTC:
        # - Europe/Kyiv is UTC+2 -> 09:00 (matches 09:00 reminder)
        # - America/New_York is EDT UTC-4 -> 03:00 (does not match 09:00 reminder)
        user_kyiv = User.objects.create_user(
            email="kyiv@example.com",
            password="Password123!",
            timezone="Europe/Kyiv",
            notifications_enabled=True,
        )
        Habit.objects.create(
            user=user_kyiv,
            name="Kyiv Morning",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        user_ny = User.objects.create_user(
            email="ny@example.com",
            password="Password123!",
            timezone="America/New_York",
            notifications_enabled=True,
        )
        Habit.objects.create(
            user=user_ny,
            name="NY Morning",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["kyiv@example.com"]

        mail.outbox.clear()

        # At 13:00 UTC, America/New_York (EDT UTC-4) is 09:00
        with freeze_time("2026-10-26 13:00:00"):
            counts_ny = send_due_notifications()
            assert counts_ny["daily_reminders_sent"] == 1
            assert len(mail.outbox) == 1
            assert mail.outbox[0].to == ["ny@example.com"]

    @freeze_time("2026-10-26 09:00:00")  # Monday
    def test_weekly_summary_respects_master_switch(self):
        user = User.objects.create_user(
            email="weekly@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=False,  # Master switch OFF
            weekly_summary_enabled=True,
        )
        Habit.objects.create(user=user, name="Coding", habit_type="boolean")

        counts = send_due_notifications(force=True)
        assert counts["weekly_summaries_sent"] == 0
        assert len(mail.outbox) == 0
