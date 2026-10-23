from __future__ import annotations

from datetime import date

from django.utils import timezone
from rest_framework import serializers

from .models import FrequencyType, Habit, HabitCheckIn


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
    is_scheduled_today = serializers.SerializerMethodField()
    frequency = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = Habit
        fields = [
            "id",
            "name",
            "description",
            "color",
            "emoji",
            "is_archived",
            "frequency_type",
            "frequency_days",
            "frequency",
            "current_streak",
            "longest_streak",
            "is_checked_today",
            "is_scheduled_today",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_archived",
            "current_streak",
            "longest_streak",
            "is_checked_today",
            "is_scheduled_today",
            "created_at",
            "updated_at",
        ]

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, "copy") else dict(data)
        if "frequency" in data_copy:
            freq = data_copy.pop("frequency")
            field_name = "frequency"
            if freq == "daily":
                data_copy["frequency_type"] = FrequencyType.DAILY
                data_copy["frequency_days"] = []
            elif isinstance(freq, list):
                if not freq:
                    raise serializers.ValidationError(
                        {field_name: "Custom frequency requires at least one weekday."}
                    )
                for day in freq:
                    if type(day) is not int or day < 0 or day > 6:
                        raise serializers.ValidationError(
                            {field_name: ("Weekdays must be integers between 0 and 6 (Monday=0).")}
                        )
                if len(freq) != len(set(freq)):
                    raise serializers.ValidationError({field_name: "Weekdays must be unique."})
                data_copy["frequency_type"] = FrequencyType.CUSTOM
                data_copy["frequency_days"] = sorted(freq)
            else:
                raise serializers.ValidationError(
                    {field_name: ("Frequency must be 'daily' or a list of weekday integers (0-6).")}
                )

        return super().to_internal_value(data_copy)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        freq_type = attrs.get(
            "frequency_type",
            self.instance.frequency_type if self.instance else FrequencyType.DAILY,
        )
        freq_days = attrs.get(
            "frequency_days",
            self.instance.frequency_days if self.instance else [],
        )

        if freq_type not in FrequencyType.values:
            raise serializers.ValidationError(
                {
                    "frequency_type": (
                        f"Invalid frequency type. Choose from: {', '.join(FrequencyType.values)}."
                    )
                }
            )

        if freq_type == FrequencyType.CUSTOM:
            if not freq_days:
                raise serializers.ValidationError(
                    {"frequency_days": "Custom frequency requires at least one weekday."}
                )
            if not isinstance(freq_days, list):
                raise serializers.ValidationError(
                    {"frequency_days": "Weekdays must be a list of integers."}
                )
            for day in freq_days:
                if type(day) is not int or day < 0 or day > 6:
                    raise serializers.ValidationError(
                        {
                            "frequency_days": (
                                "Weekdays must be integers between 0 and 6 (Monday=0)."
                            )
                        }
                    )
            if len(freq_days) != len(set(freq_days)):
                raise serializers.ValidationError({"frequency_days": "Weekdays must be unique."})
            attrs["frequency_days"] = sorted(freq_days)
        elif freq_type == FrequencyType.DAILY:
            if (
                self.instance
                and self.instance.frequency_type == FrequencyType.DAILY
                and "frequency_type" not in attrs
                and "frequency_days" in attrs
                and attrs["frequency_days"]
            ):
                raise serializers.ValidationError(
                    {
                        "frequency_days": (
                            "Cannot set frequency_days for a daily habit. Change frequency_type to 'custom'."
                        )
                    }
                )
            attrs["frequency_days"] = []

        return attrs

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

    def get_is_scheduled_today(self, obj: Habit) -> bool:
        """Check whether the habit is scheduled for today (or requested target date)."""
        target_date = self._get_target_date(obj)
        return obj.is_scheduled_on(target_date)


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
