from datetime import date

from django.utils import timezone
from rest_framework import serializers

from .models import Habit, HabitCheckIn
from .services.streaks import calculate_habit_streaks


class HabitCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitCheckIn
        fields = ["id", "date", "created_at"]
        read_only_fields = ["id", "created_at"]


class CheckInFilterSerializer(serializers.Serializer):
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)


class HabitSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()
    longest_streak = serializers.SerializerMethodField()
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

    def _get_target_date(self, obj=None) -> date:
        request = self.context.get("request")
        if request and "date" in request.query_params:
            try:
                return serializers.DateField().to_internal_value(request.query_params["date"])
            except serializers.ValidationError:
                pass
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

    def get_is_checked_today(self, obj) -> bool:
        target_date = self._get_target_date(obj)
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "check_ins" in obj._prefetched_objects_cache
        ):
            return any(ci.date == target_date for ci in obj.check_ins.all())
        return obj.check_ins.filter(date=target_date).exists()

    def _get_streaks(self, obj):
        if not hasattr(obj, "_streaks_cache"):
            obj._streaks_cache = calculate_habit_streaks(obj)
        return obj._streaks_cache

    def get_current_streak(self, obj) -> int:
        return self._get_streaks(obj).current_streak

    def get_longest_streak(self, obj) -> int:
        return self._get_streaks(obj).longest_streak


class CheckInActionSerializer(serializers.Serializer):
    date = serializers.DateField(required=False, default=None)


class ArchiveResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    is_archived = serializers.BooleanField()


class CheckInResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    habit_id = serializers.IntegerField()
    date = serializers.DateField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
