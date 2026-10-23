from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .validators import hex_color_validator, validate_emoji


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
