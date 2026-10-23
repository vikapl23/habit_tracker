from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

class Habit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='habits',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    color = models.CharField(max_length=7, default='#3B82F6')
    emoji = models.CharField(max_length=16, default='🎯')
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_archived', 'created_at']),
        ]

    def __str__(self):
        return self.name


class HabitCheckIn(models.Model):
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name='check_ins'
    )
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['habit', 'date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['habit', 'date'],
                name='unique_habit_checkin_per_date'
            )
        ]

    def clean(self):
        super().clean()
        if self.date and self.date > timezone.localdate():
            raise ValidationError({'date': 'Check-ins cannot be recorded for future dates.'})

    def __str__(self):
        return f"{self.habit.name} - {self.date}"


# Alias CheckIn to HabitCheckIn for clean API / import compatibility
CheckIn = HabitCheckIn
