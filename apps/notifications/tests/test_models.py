from __future__ import annotations

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.notifications.models import NotificationLog

User = get_user_model()


@pytest.mark.django_db
class TestNotificationLogModel:
    def test_create_notification_log(self):
        user = User.objects.create_user(email="user@example.com", password="Password123!")
        today = datetime.date(2026, 10, 26)
        log = NotificationLog.objects.create(
            user=user,
            notification_type="daily_reminder",
            scheduled_date=today,
            recipient_email=user.email,
            details={"incomplete_habits_count": 2},
        )
        assert log.id is not None
        assert log.user == user
        assert log.notification_type == "daily_reminder"
        assert log.scheduled_date == today
        assert log.recipient_email == "user@example.com"
        assert log.details["incomplete_habits_count"] == 2
        assert "daily_reminder" in str(log)

    def test_duplicate_notification_on_same_date_fails(self):
        user = User.objects.create_user(email="user@example.com", password="Password123!")
        today = datetime.date(2026, 10, 26)
        NotificationLog.objects.create(
            user=user,
            notification_type="daily_reminder",
            scheduled_date=today,
            recipient_email=user.email,
        )

        with pytest.raises(IntegrityError):
            NotificationLog.objects.create(
                user=user,
                notification_type="daily_reminder",
                scheduled_date=today,
                recipient_email=user.email,
            )

    def test_different_notification_types_allowed_on_same_date(self):
        user = User.objects.create_user(email="user@example.com", password="Password123!")
        today = datetime.date(2026, 10, 26)
        log1 = NotificationLog.objects.create(
            user=user,
            notification_type="daily_reminder",
            scheduled_date=today,
            recipient_email=user.email,
        )
        log2 = NotificationLog.objects.create(
            user=user,
            notification_type="weekly_summary",
            scheduled_date=today,
            recipient_email=user.email,
        )
        assert log1.id != log2.id

    def test_habit_notification_log_uniqueness_per_day(self):
        from apps.habits.models import Habit

        user = User.objects.create_user(email="user@example.com", password="Password123!")
        today = datetime.date(2026, 10, 26)
        h1 = Habit.objects.create(user=user, name="Habit 1")
        h2 = Habit.objects.create(user=user, name="Habit 2")

        # Two different habits for same user on same day are allowed
        log1 = NotificationLog.objects.create(
            user=user,
            habit=h1,
            notification_type="daily_reminder",
            scheduled_date=today,
            recipient_email=user.email,
        )
        log2 = NotificationLog.objects.create(
            user=user,
            habit=h2,
            notification_type="daily_reminder",
            scheduled_date=today,
            recipient_email=user.email,
        )
        assert log1.id != log2.id

        # Duplicate log for same habit on same day fails
        with pytest.raises(IntegrityError):
            NotificationLog.objects.create(
                user=user,
                habit=h1,
                notification_type="daily_reminder",
                scheduled_date=today,
                recipient_email=user.email,
            )
