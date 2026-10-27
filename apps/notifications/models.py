from __future__ import annotations

from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    """
    Audit log of dispatched notifications to prevent duplicate deliveries.
    Enforces uniqueness per (habit, scheduled_date) for habit reminders,
    and (user, notification_type, scheduled_date) for user-level notifications.
    """

    class NotificationType(models.TextChoices):
        HABIT_REMINDER = "habit_reminder", "Habit Reminder"
        DAILY_REMINDER = "daily_reminder", "Daily Reminder"
        WEEKLY_SUMMARY = "weekly_summary", "Weekly Summary"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_logs",
    )
    habit = models.ForeignKey(
        "habits.Habit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
    )
    scheduled_date = models.DateField(
        help_text="Target date (for habit reminder) or start-of-week Monday (for weekly summary).",
    )
    recipient_email = models.EmailField()
    sent_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadata about the email (e.g. habits list, stats).",
    )

    class Meta:
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "scheduled_date"],
                condition=models.Q(habit__isnull=False),
                name="unique_habit_notification_per_date",
            ),
            models.UniqueConstraint(
                fields=["user", "notification_type", "scheduled_date"],
                condition=models.Q(habit__isnull=True),
                name="unique_user_notification_per_date",
            ),
        ]
        indexes = [
            models.Index(fields=["habit", "scheduled_date"]),
            models.Index(fields=["user", "notification_type", "scheduled_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.notification_type} on {self.scheduled_date}"
