from rest_framework import serializers
from django.utils import timezone
from .models import Habit, CheckIn, HabitCheckIn

class HabitCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitCheckIn
        fields = ['id', 'date', 'created_at']
        read_only_fields = ['id', 'created_at']


# Alias for convenience
CheckInSerializer = HabitCheckInSerializer


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = [
            'id',
            'name',
            'description',
            'color',
            'emoji',
            'is_archived',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_archived', 'created_at', 'updated_at']


class CheckInActionSerializer(serializers.Serializer):
    date = serializers.DateField(required=False, default=None)

    def validate_date(self, value):
        if value is not None and value > timezone.localdate():
            raise serializers.ValidationError("Check-ins cannot be recorded for future dates.")
        return value
