from __future__ import annotations

from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    """
    Audit log of dispatched notifications to prevent duplicate deliveries.
    Enforces uniqueness per (user, notification_type, scheduled_date).
    """

    class NotificationType(models.TextChoices):
        DAILY_REMINDER = "daily_reminder", "Daily Reminder"
        WEEKLY_SUMMARY = "weekly_summary", "Weekly Summary"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_logs",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
    )
    scheduled_date = models.DateField(
        help_text="Target date (for daily reminder) or start-of-week Monday (for weekly summary).",
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
                fields=["user", "notification_type", "scheduled_date"],
                name="unique_user_notification_per_date",
            )
        ]
        indexes = [
            models.Index(fields=["user", "notification_type", "scheduled_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.notification_type} on {self.scheduled_date}"
