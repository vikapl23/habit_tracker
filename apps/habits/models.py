from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .validators import hex_color_validator, validate_emoji


class FrequencyType(models.TextChoices):
    DAILY = "daily", "Daily"
    CUSTOM = "custom", "Custom"


class Habit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    color = models.CharField(max_length=7, default="#3B82F6", validators=[hex_color_validator])
    emoji = models.CharField(max_length=16, default="🎯", validators=[validate_emoji])
    is_archived = models.BooleanField(default=False)
    frequency_type = models.CharField(
        max_length=10,
        choices=FrequencyType.choices,
        default=FrequencyType.DAILY,
    )
    frequency_days = models.JSONField(
        default=list,
        blank=True,
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_check_in_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_archived", "-created_at"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.frequency_type not in FrequencyType.values:
            raise ValidationError(
                {
                    "frequency_type": (
                        f"Invalid frequency type. Choose from: {', '.join(FrequencyType.values)}."
                    )
                }
            )

        if self.frequency_type == FrequencyType.CUSTOM:
            if not self.frequency_days:
                raise ValidationError(
                    {"frequency_days": "Custom frequency requires at least one weekday."}
                )
            if not isinstance(self.frequency_days, list):
                raise ValidationError({"frequency_days": "Weekdays must be a list of integers."})
            for day in self.frequency_days:
                if type(day) is not int or day < 0 or day > 6:
                    raise ValidationError(
                        {"frequency_days": "Weekdays must be integers between 0 and 6 (Monday=0)."}
                    )
            if len(self.frequency_days) != len(set(self.frequency_days)):
                raise ValidationError({"frequency_days": "Weekdays must be unique."})
        elif self.frequency_type == FrequencyType.DAILY:
            if self.frequency_days:
                self.frequency_days = []

    def is_scheduled_on(self, target: date | int) -> bool:
        """Return True if the habit is scheduled on target (date or weekday integer 0-6)."""
        if self.frequency_type == FrequencyType.DAILY:
            return True
        weekday = target.weekday() if hasattr(target, "weekday") else target
        return weekday in self.frequency_days

    def is_scheduled_today(self, reference_date: date | None = None) -> bool:
        """Return True if the habit is scheduled today (relative to user's timezone)."""
        if reference_date is None:
            user = getattr(self, "user", None)
            if user and hasattr(user, "get_today"):
                reference_date = user.get_today()
            else:
                reference_date = timezone.localdate()
        return self.is_scheduled_on(reference_date)

    def save(self, *args, **kwargs):
        if self.frequency_type == FrequencyType.CUSTOM and isinstance(self.frequency_days, list):
            self.frequency_days = sorted(self.frequency_days)
        elif self.frequency_type == FrequencyType.DAILY:
            self.frequency_days = []

        update_fields = kwargs.get("update_fields")
        frequency_changed = False
        if self.pk:
            if (
                update_fields is None
                or "frequency_type" in update_fields
                or "frequency_days" in update_fields
            ):
                orig = (
                    Habit.objects.filter(pk=self.pk)
                    .values("frequency_type", "frequency_days")
                    .first()
                )
                if orig and (
                    orig["frequency_type"] != self.frequency_type
                    or orig["frequency_days"] != self.frequency_days
                ):
                    frequency_changed = True

        super().save(*args, **kwargs)

        if frequency_changed:
            from apps.habits.services.streaks import recalculate_habit_streaks

            recalculate_habit_streaks(self)

    def get_current_streak(self, reference_date=None) -> int:
        """
        Return the current streak evaluated at reference_date (defaults to user's today).
        If days have passed without check-ins, returns 0 without querying the database.
        """
        if not self.last_check_in_date or self.current_streak == 0:
            return 0

        if reference_date is None:
            user = getattr(self, "user", None)
            if user and hasattr(user, "get_today"):
                reference_date = user.get_today()
            else:
                reference_date = timezone.localdate()

        days_since = (reference_date - self.last_check_in_date).days
        if days_since <= 1:
            return self.current_streak
        return 0


class HabitCheckIn(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="check_ins")
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["habit", "date"], name="unique_habit_checkin_per_date")
        ]

    def __str__(self):
        return f"{self.habit.name} - {self.date}"


@receiver([post_save, post_delete], sender=HabitCheckIn)
def on_checkin_saved_or_deleted(sender, instance, **kwargs):
    from apps.habits.services.streaks import recalculate_habit_streaks

    if instance.habit_id:
        try:
            recalculate_habit_streaks(instance.habit)
        except Exception:
            pass
