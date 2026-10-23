from django.conf import settings
from django.db import models

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_archived", "-created_at"]),
        ]

    def __str__(self):
        return self.name


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
