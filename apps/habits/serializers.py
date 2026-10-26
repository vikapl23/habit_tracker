from __future__ import annotations

from datetime import date

from django.utils import timezone
from rest_framework import serializers

from .models import FrequencyType, Habit, HabitCheckIn, HabitType
from .services.completion import is_day_completed


class HabitDecimalField(serializers.DecimalField):
    """Decimal field for habit amounts with at most 2 decimal places serialized as float."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 8)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("coerce_to_string", False)
        super().__init__(**kwargs)

    def to_representation(self, value):
        val = super().to_representation(value)
        return float(val) if val is not None else None


class HabitCheckInSerializer(serializers.ModelSerializer):
    """Serializer for habit check-in records."""

    value = HabitDecimalField(read_only=True)

    class Meta:
        model = HabitCheckIn
        fields = ["id", "date", "value", "created_at"]
        read_only_fields = ["id", "value", "created_at"]


class CheckInFilterSerializer(serializers.Serializer):
    """Serializer for validating query parameters when filtering check-in records."""

    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)


class HabitSerializer(serializers.ModelSerializer):
    """Serializer for Habit model representation and creation."""

    current_streak = serializers.SerializerMethodField()
    is_checked_today = serializers.SerializerMethodField()
    is_scheduled_today = serializers.SerializerMethodField()
    today_value = serializers.SerializerMethodField()
    today_progress = serializers.SerializerMethodField()
    target_value = HabitDecimalField(required=False, allow_null=True)
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
            "habit_type",
            "unit",
            "target_value",
            "today_value",
            "today_progress",
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
            "today_value",
            "today_progress",
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
        habit_type = attrs.get(
            "habit_type",
            self.instance.habit_type if self.instance else HabitType.BOOLEAN,
        )
        target_value = attrs.get(
            "target_value",
            self.instance.target_value if self.instance else None,
        )
        unit = attrs.get(
            "unit",
            self.instance.unit if self.instance else "",
        )

        if habit_type == HabitType.MEASURABLE:
            if not unit or not unit.strip():
                raise serializers.ValidationError(
                    {"unit": "Unit is required for measurable habits."}
                )
            if target_value is None:
                raise serializers.ValidationError(
                    {"target_value": "Target value is required for measurable habits."}
                )
            if target_value <= 0:
                raise serializers.ValidationError(
                    {"target_value": "Target value must be greater than zero."}
                )
            if target_value > 100000:
                raise serializers.ValidationError(
                    {"target_value": "Target value cannot exceed 100,000."}
                )
        elif habit_type == HabitType.BOOLEAN:
            if unit:
                raise serializers.ValidationError(
                    {"unit": "Unit cannot be set for boolean habits."}
                )
            if target_value is not None:
                raise serializers.ValidationError(
                    {"target_value": "Target value cannot be set for boolean habits."}
                )

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

    def _get_target_checkin(self, obj: Habit) -> HabitCheckIn | None:
        if hasattr(obj, "_cached_target_checkin"):
            return obj._cached_target_checkin
        if "checkins_map" in self.context:
            ci = self.context["checkins_map"].get(obj.id)
            obj._cached_target_checkin = ci
            return ci
        target_date = self._get_target_date(obj)
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "check_ins" in obj._prefetched_objects_cache
        ):
            for ci in obj.check_ins.all():
                if ci.date == target_date:
                    obj._cached_target_checkin = ci
                    return ci
            obj._cached_target_checkin = None
            return None
        ci = obj.check_ins.filter(date=target_date).first()
        obj._cached_target_checkin = ci
        return ci

    def get_today_value(self, obj: Habit) -> float:
        target_date = self._get_target_date(obj)
        if "checkins_map" in self.context:
            checkin = self.context["checkins_map"].get(obj.id)
            return float(checkin.value) if checkin else 0.0

        user_today = self._get_user_today(obj)
        if obj.habit_type == HabitType.BOOLEAN and target_date == user_today:
            if obj.last_check_in_date == user_today:
                return float(obj.last_check_in_value)
            return 0.0

        checkin = self._get_target_checkin(obj)
        return float(checkin.value) if checkin else 0.0

    def get_today_progress(self, obj: Habit) -> float:
        target_date = self._get_target_date(obj)
        if "checkins_map" in self.context:
            checkin = self.context["checkins_map"].get(obj.id)
            val = float(checkin.value) if checkin else 0.0
        else:
            user_today = self._get_user_today(obj)
            if obj.habit_type == HabitType.BOOLEAN and target_date == user_today:
                if obj.last_check_in_date == user_today:
                    val = float(obj.last_check_in_value)
                else:
                    val = 0.0
            else:
                checkin = self._get_target_checkin(obj)
                val = float(checkin.value) if checkin else 0.0

        if val <= 0:
            return 0.0
        if obj.habit_type == HabitType.BOOLEAN:
            return 100.0
        target = float(obj.target_value) if obj.target_value else 0.0
        if target <= 0:
            return 0.0
        return min(100.0, round((val / target) * 100, 1))

    def get_is_checked_today(self, obj: Habit) -> bool:
        """Check whether the habit is completed for today (or requested date)."""
        target_date = self._get_target_date(obj)
        if "checkins_map" in self.context:
            checkin = self.context["checkins_map"].get(obj.id)
            if not checkin:
                return False
            return is_day_completed(obj, checkin)

        user_today = self._get_user_today(obj)
        if target_date == user_today:
            if obj.last_check_in_date == user_today:
                return is_day_completed(obj, obj.last_check_in_value)
            return False

        if obj.last_check_in_date is None:
            return False
        if obj.last_check_in_date != target_date:
            if target_date > obj.last_check_in_date:
                return False
            if (
                not hasattr(obj, "_prefetched_objects_cache")
                or "check_ins" not in obj._prefetched_objects_cache
            ):
                return False

        checkin = self._get_target_checkin(obj)
        if not checkin:
            return False
        return is_day_completed(obj, checkin)

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
    value = HabitDecimalField(required=False, default=None, min_value=0, max_value=100000)
    mode = serializers.ChoiceField(choices=["add", "set"], required=False, default="add")


class UncheckActionSerializer(serializers.Serializer):
    """Serializer for uncheck action payloads."""

    date = serializers.DateField(required=False, default=None)
    value = HabitDecimalField(required=False, default=None, min_value=0, max_value=100000)


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
    today_value = serializers.FloatField()
    today_progress = serializers.FloatField()
    is_completed = serializers.BooleanField()


class HabitStatisticsSerializer(serializers.Serializer):
    """Serializer for individual habit statistics payload."""

    habit_id = serializers.IntegerField()
    completion_rate_7d = serializers.FloatField()
    completion_rate_30d = serializers.FloatField()
    total_check_ins = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()


class BestHabitSummarySerializer(serializers.Serializer):
    """Serializer for the top performing habit summary."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    emoji = serializers.CharField()
    color = serializers.CharField()
    completion_rate_30d = serializers.FloatField()


class UserSummaryStatisticsSerializer(serializers.Serializer):
    """Serializer for overall user dashboard statistics summary."""

    overall_completion_rate_week = serializers.FloatField()
    overall_completion_rate_month = serializers.FloatField()
    best_habit = BestHabitSummarySerializer(allow_null=True)
    total_active_habits = serializers.IntegerField()
    total_check_ins = serializers.IntegerField()
