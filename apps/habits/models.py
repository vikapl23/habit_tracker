import threading
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .validators import hex_color_validator, validate_emoji


class HabitType(models.TextChoices):
    BOOLEAN = "boolean", "Boolean"
    MEASURABLE = "measurable", "Measurable"


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
    habit_type = models.CharField(
        max_length=20,
        choices=HabitType.choices,
        default=HabitType.BOOLEAN,
    )
    target_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    unit = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )
    frequency_type = models.CharField(
        max_length=10,
        choices=FrequencyType.choices,
        default=FrequencyType.DAILY,
    )
    frequency_days = models.JSONField(
        default=list,
        blank=True,
    )
    reminder_enabled = models.BooleanField(
        default=False,
        help_text="Whether email reminder is enabled for this habit.",
    )
    reminder_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Reminder time in user's local timezone (minutes must be 0, 15, 30, or 45).",
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_check_in_date = models.DateField(null=True, blank=True)
    last_check_in_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
    )
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
        if self.habit_type not in HabitType.values:
            raise ValidationError(
                {"habit_type": f"Invalid habit type. Choose from: {', '.join(HabitType.values)}."}
            )

        if self.habit_type == HabitType.MEASURABLE:
            if not self.unit or not self.unit.strip():
                raise ValidationError({"unit": "Unit is required for measurable habits."})
            if self.target_value is None:
                raise ValidationError(
                    {"target_value": "Target value is required for measurable habits."}
                )
            if self.target_value <= Decimal("0"):
                raise ValidationError({"target_value": "Target value must be greater than zero."})
            if self.target_value > Decimal("100000.00"):
                raise ValidationError({"target_value": "Target value cannot exceed 100,000."})
        elif self.habit_type == HabitType.BOOLEAN:
            if self.unit:
                raise ValidationError({"unit": "Unit cannot be set for boolean habits."})
            if self.target_value is not None:
                raise ValidationError(
                    {"target_value": "Target value cannot be set for boolean habits."}
                )

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

        if self.reminder_enabled:
            if self.reminder_time is None:
                raise ValidationError(
                    {"reminder_time": "Reminder time is required when reminder is enabled."}
                )
        if self.reminder_time is not None:
            if self.reminder_time.minute not in (0, 15, 30, 45):
                raise ValidationError(
                    {"reminder_time": "Reminder time minutes must be 0, 15, 30, or 45."}
                )

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "frequency_type" in field_names:
            instance._loaded_frequency_type = values[field_names.index("frequency_type")]
        if "frequency_days" in field_names:
            raw_days = values[field_names.index("frequency_days")]
            instance._loaded_frequency_days = (
                list(raw_days) if isinstance(raw_days, list) else raw_days
            )
        return instance

    def is_scheduled_on(self, target: date | int) -> bool:
        """Return True if the habit is scheduled on target (date or weekday integer 0-6)."""
        if self.frequency_type == FrequencyType.DAILY:
            return True
        weekday = target.weekday() if hasattr(target, "weekday") else target
        return weekday in (self.frequency_days or [])

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
        self.clean()
        if self.frequency_type == FrequencyType.CUSTOM and isinstance(self.frequency_days, list):
            self.frequency_days = sorted(self.frequency_days)
        elif self.frequency_type == FrequencyType.DAILY:
            self.frequency_days = []

        super().save(*args, **kwargs)

        self._loaded_frequency_type = self.frequency_type
        self._loaded_frequency_days = (
            list(self.frequency_days)
            if isinstance(self.frequency_days, list)
            else self.frequency_days
        )

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

        if self.last_check_in_date == reference_date:
            return self.current_streak

        if self.last_check_in_date > reference_date:
            from apps.habits.services.streaks import calculate_habit_streaks

            return calculate_habit_streaks(self, reference_date=reference_date).current_streak

        # Check if any scheduled days were missed between last_check_in_date and reference_date
        check_date = self.last_check_in_date + timedelta(days=1)
        while check_date < reference_date:
            if self.is_scheduled_on(check_date):
                return 0
            check_date += timedelta(days=1)

        return self.current_streak


class HabitCheckIn(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="check_ins")
    date = models.DateField()
    value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("1.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["habit", "date"], name="unique_habit_checkin_per_date")
        ]

    def __str__(self):
        return f"{self.habit.name} - {self.date}"


_streak_signals_suppressed = threading.local()


class suppress_streak_signals:
    """Context manager to suppress automatic post_save/post_delete streak calculation signals."""

    def __enter__(self):
        _streak_signals_suppressed.value = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _streak_signals_suppressed.value = False


def are_streak_signals_suppressed() -> bool:
    return getattr(_streak_signals_suppressed, "value", False)


@receiver([post_save, post_delete], sender=HabitCheckIn)
def on_checkin_saved_or_deleted(sender, instance, **kwargs):
    if are_streak_signals_suppressed():
        return

    from apps.habits.services.streaks import recalculate_habit_streaks

    if instance.habit_id:
        try:
            user = getattr(instance.habit, "user", None)
            ref_date = (
                user.get_today() if user and hasattr(user, "get_today") else timezone.localdate()
            )
            recalculate_habit_streaks(instance.habit, reference_date=ref_date)
        except Exception:
            pass
