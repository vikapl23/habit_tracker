from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from anymail.exceptions import AnymailAPIError
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import EmailMultiAlternatives
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

    @freeze_time("2026-10-26 09:25:00")
    def test_cron_runs_25_minutes_late_reminder_is_still_sent_once(self):
        user = User.objects.create_user(
            email="late_cron@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit = Habit.objects.create(
            user=user,
            name="Morning Run",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )
        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        assert NotificationLog.objects.filter(
            habit=habit, scheduled_date=datetime.date(2026, 10, 26)
        ).exists()

        mail.outbox.clear()

        # Run again 10 minutes later: already sent today, should not send again
        with freeze_time("2026-10-26 09:35:00"):
            counts2 = send_due_notifications()
            assert counts2["daily_reminders_sent"] == 0
            assert len(mail.outbox) == 0

    @freeze_time("2026-10-27 09:00:00")  # Tuesday
    def test_reminder_not_sent_for_unscheduled_day_even_if_missed_yesterday(self):
        user = User.objects.create_user(
            email="yesterday_missed@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        # Habit only scheduled on Mondays (day 0)
        habit = Habit.objects.create(
            user=user,
            name="Monday Task",
            habit_type="boolean",
            frequency_type=FrequencyType.CUSTOM,
            frequency_days=[0],
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )
        # On Tuesday, even though reminder wasn't sent on Monday, it should not send today
        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 0
        assert not NotificationLog.objects.filter(habit=habit).exists()

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

    @freeze_time("2026-10-26 09:00:00")
    def test_log_row_claimed_before_sending_email(self):
        user = User.objects.create_user(
            email="claim_first@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit = Habit.objects.create(
            user=user,
            name="Meditate",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        log_existed_during_send = []

        def fake_send(*args, **kwargs):
            exists = NotificationLog.objects.filter(
                habit=habit, scheduled_date=datetime.date(2026, 10, 26)
            ).exists()
            log_existed_during_send.append(exists)
            return 1

        with patch("django.core.mail.EmailMultiAlternatives.send", side_effect=fake_send):
            counts = send_due_notifications()
            assert counts["daily_reminders_sent"] == 1

        assert log_existed_during_send == [True]

    @freeze_time("2026-10-26 09:00:00")
    def test_concurrent_claim_aborts_duplicate_email(self):
        user = User.objects.create_user(
            email="concurrent@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit = Habit.objects.create(
            user=user,
            name="Jog",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        # Pre-claim the row directly as if another concurrent worker just claimed it
        NotificationLog.objects.create(
            user=user,
            habit=habit,
            notification_type=NotificationLog.NotificationType.HABIT_REMINDER,
            scheduled_date=datetime.date(2026, 10, 26),
            recipient_email=user.email,
        )

        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 0
        assert len(mail.outbox) == 0

    @freeze_time("2026-10-26 09:00:00")
    def test_send_failure_releases_claimed_log_row_so_next_run_retries(self):
        user = User.objects.create_user(
            email="retry@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit = Habit.objects.create(
            user=user,
            name="Run",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        with patch(
            "django.core.mail.EmailMultiAlternatives.send",
            side_effect=RuntimeError("Mailgun down"),
        ):
            counts = send_due_notifications()
            assert counts["daily_reminders_sent"] == 0

        # Verify the claimed log was released (deleted)
        assert not NotificationLog.objects.filter(habit=habit).exists()

        # Next run succeeds
        counts = send_due_notifications()
        assert counts["daily_reminders_sent"] == 1
        assert len(mail.outbox) == 1
        assert NotificationLog.objects.filter(habit=habit).exists()

    @freeze_time("2026-10-26 09:00:00")  # Monday
    def test_weekly_summary_claimed_before_sending_email_and_released_on_failure(self):
        user = User.objects.create_user(
            email="weekly_claim@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
            weekly_summary_enabled=True,
        )
        Habit.objects.create(
            user=user,
            name="Weekly Habit",
            habit_type="boolean",
        )

        with patch(
            "django.core.mail.EmailMultiAlternatives.send",
            side_effect=RuntimeError("Mailgun weekly failure"),
        ):
            counts = send_due_notifications()
            assert counts["weekly_summaries_sent"] == 0

        # Should be released on failure
        assert not NotificationLog.objects.filter(
            user=user,
            notification_type=NotificationLog.NotificationType.WEEKLY_SUMMARY,
        ).exists()

        # Next run succeeds
        counts = send_due_notifications()
        assert counts["weekly_summaries_sent"] == 1
        assert NotificationLog.objects.filter(
            user=user,
            notification_type=NotificationLog.NotificationType.WEEKLY_SUMMARY,
        ).exists()

    @freeze_time("2026-10-26 09:00:00")
    def test_send_due_notifications_avoids_n_plus_one_when_not_due(self, django_assert_num_queries):
        # Create 10 users with habits that are not due yet (reminder_time at 20:00)
        for i in range(10):
            u = User.objects.create_user(
                email=f"notdue_{i}@example.com",
                password="Password123!",
                timezone="UTC",
                notifications_enabled=True,
            )
            Habit.objects.create(
                user=u,
                name=f"Evening Habit {i}",
                habit_type="boolean",
                reminder_enabled=True,
                reminder_time=datetime.time(20, 0),
            )

        # Constant queries regardless of user count
        with django_assert_num_queries(2):
            counts = send_due_notifications()
            assert counts["daily_reminders_sent"] == 0

    @freeze_time("2026-10-26 09:00:00")
    def test_send_due_notifications_query_count_bounded_when_habits_due(
        self, django_assert_num_queries
    ):
        for i in range(5):
            u = User.objects.create_user(
                email=f"due_user_{i}@example.com",
                password="Password123!",
                timezone="UTC",
                notifications_enabled=True,
            )
            for j in range(2):
                Habit.objects.create(
                    user=u,
                    name=f"Habit {i}_{j}",
                    habit_type="boolean",
                    reminder_enabled=True,
                    reminder_time=datetime.time(9, 0),
                )

        # 4 setup/lookup queries + 3 queries (savepoint, bulk insert, release) per user
        # 4 + (5 * 3) = 19 queries total for 5 users across 10 habits
        with django_assert_num_queries(19):
            counts = send_due_notifications()
            assert counts["daily_reminders_sent"] == 5

    @freeze_time("2026-10-26 09:00:00")
    def test_mailgun_api_error_releases_log_and_continues_processing_other_users(self):
        user_fail = User.objects.create_user(
            email="fail_mailgun@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit_fail = Habit.objects.create(
            user=user_fail,
            name="Fail Habit",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        user_ok = User.objects.create_user(
            email="ok_mailgun@example.com",
            password="Password123!",
            timezone="UTC",
            notifications_enabled=True,
        )
        habit_ok = Habit.objects.create(
            user=user_ok,
            name="OK Habit",
            habit_type="boolean",
            reminder_enabled=True,
            reminder_time=datetime.time(9, 0),
        )

        orig_send = EmailMultiAlternatives.send

        def mock_send(msg_self, *args, **kwargs):
            if "fail_mailgun@example.com" in msg_self.to:
                raise AnymailAPIError("Mailgun 500 API Error")
            return orig_send(msg_self, *args, **kwargs)

        with patch.object(EmailMultiAlternatives, "send", mock_send):
            counts = send_due_notifications()
            # Only user_ok succeeded
            assert counts["daily_reminders_sent"] == 1

        # user_fail claimed log was released
        assert not NotificationLog.objects.filter(habit=habit_fail).exists()
        # user_ok claimed log was kept
        assert NotificationLog.objects.filter(habit=habit_ok).exists()

        # On subsequent retry when Mailgun recovers, user_fail is sent
        counts2 = send_due_notifications()
        assert counts2["daily_reminders_sent"] == 1
        assert NotificationLog.objects.filter(habit=habit_fail).exists()

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
