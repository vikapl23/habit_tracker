from __future__ import annotations

from datetime import date

from django.utils import timezone
from rest_framework import serializers

from .models import Habit, HabitCheckIn


class HabitCheckInSerializer(serializers.ModelSerializer):
    """Serializer for habit check-in records."""

    class Meta:
        model = HabitCheckIn
        fields = ["id", "date", "created_at"]
        read_only_fields = ["id", "created_at"]


class CheckInFilterSerializer(serializers.Serializer):
    """Serializer for validating query parameters when filtering check-in records."""

    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)


class HabitSerializer(serializers.ModelSerializer):
    """Serializer for Habit model representation and creation."""

    current_streak = serializers.SerializerMethodField()
    is_checked_today = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            "id",
            "name",
            "description",
            "color",
            "emoji",
            "is_archived",
            "current_streak",
            "longest_streak",
            "is_checked_today",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_archived",
            "current_streak",
            "longest_streak",
            "is_checked_today",
            "created_at",
            "updated_at",
        ]

    def _get_user_today(self, obj: Habit | None = None) -> date:
        """Determine today's date in the context user's timezone."""
        request = self.context.get("request")
        if (
            request
            and getattr(request, "user", None)
            and request.user.is_authenticated
            and hasattr(request.user, "get_today")
        ):
            return request.user.get_today()
        if obj and getattr(obj, "user", None) and hasattr(obj.user, "get_today"):
            return obj.user.get_today()
        return timezone.localdate()

    def _get_target_date(self, obj: Habit | None = None) -> date:
        """Extract target date from query parameters or default to user's today."""
        request = self.context.get("request")
        if request and "date" in request.query_params:
            try:
                return serializers.DateField().to_internal_value(request.query_params["date"])
            except serializers.ValidationError:
                pass
        return self._get_user_today(obj)

    def get_is_checked_today(self, obj: Habit) -> bool:
        """Check whether the habit has a check-in recorded for today."""
        target_date = self._get_target_date(obj)
        if obj.last_check_in_date is None:
            return False
        if obj.last_check_in_date == target_date:
            return True
        if target_date > obj.last_check_in_date:
            return False
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "check_ins" in obj._prefetched_objects_cache
        ):
            return any(ci.date == target_date for ci in obj.check_ins.all())
        return obj.check_ins.filter(date=target_date).exists()

    def get_current_streak(self, obj: Habit) -> int:
        """Calculate the habit's current streak as of user's today."""
        user_today = self._get_user_today(obj)
        return obj.get_current_streak(reference_date=user_today)


class CheckInActionSerializer(serializers.Serializer):
    """Serializer for check-in action payloads."""

    date = serializers.DateField(required=False, default=None)


class ArchiveResponseSerializer(serializers.Serializer):
    """Serializer for archive/unarchive response payload."""

    id = serializers.IntegerField()
    is_archived = serializers.BooleanField()


class CheckInResponseSerializer(serializers.Serializer):
    """Serializer for check-in operation response payload."""

    status = serializers.CharField()
    habit_id = serializers.IntegerField()
    date = serializers.DateField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
