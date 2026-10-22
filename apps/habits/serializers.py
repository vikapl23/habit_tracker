from rest_framework import serializers
from django.utils import timezone
from .models import Habit, HabitCheckIn
from .services.streaks import calculate_streaks

class HabitCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitCheckIn
        fields = ['id', 'date', 'created_at']
        read_only_fields = ['id', 'created_at']


class HabitSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()
    longest_streak = serializers.SerializerMethodField()
    is_checked_today = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id',
            'name',
            'description',
            'color',
            'emoji',
            'is_archived',
            'current_streak',
            'longest_streak',
            'is_checked_today',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_archived', 'created_at', 'updated_at']

    def _get_streaks_and_status(self, obj):
        # Cache per-instance on serializer to avoid redundant calculations across method fields
        if not hasattr(obj, '_cached_streak_data'):
            request = self.context.get('request')
            ref_date = None
            if request and hasattr(request, 'query_params'):
                date_str = request.query_params.get('date')
                if date_str:
                    try:
                        from datetime import datetime
                        ref_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        ref_date = None

            if ref_date is None:
                ref_date = timezone.localdate()

            checkin_dates = set(obj.check_ins.values_list('date', flat=True))
            current_streak, longest_streak = calculate_streaks(checkin_dates, reference_date=ref_date)
            is_checked = ref_date in checkin_dates
            obj._cached_streak_data = {
                'current_streak': current_streak,
                'longest_streak': longest_streak,
                'is_checked_today': is_checked,
            }
        return obj._cached_streak_data

    def get_current_streak(self, obj):
        return self._get_streaks_and_status(obj)['current_streak']

    def get_longest_streak(self, obj):
        return self._get_streaks_and_status(obj)['longest_streak']

    def get_is_checked_today(self, obj):
        return self._get_streaks_and_status(obj)['is_checked_today']


class CheckInActionSerializer(serializers.Serializer):
    date = serializers.DateField(required=False, default=None)

    def validate_date(self, value):
        if value is not None and value > timezone.localdate():
            raise serializers.ValidationError("Check-ins cannot be recorded for future dates.")
        return value
