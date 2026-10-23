import zoneinfo

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    timezone = serializers.CharField(required=False, default="Europe/Kyiv")

    def validate_timezone(self, value):
        if value not in zoneinfo.available_timezones():
            raise serializers.ValidationError(f"'{value}' is not a valid IANA time zone.")
        return value

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)
        if isinstance(data, dict) and "email" in data and isinstance(data["email"], str):
            data["email"] = data["email"].lower()
        return super().to_internal_value(data)

    def create(self, validated_data):
        email = validated_data["email"].lower()
        tz = validated_data.get("timezone", "Europe/Kyiv")
        try:
            if not User.objects.filter(email=email).exists():
                return User.objects.create_user(
                    email=email,
                    password=validated_data["password"],
                    timezone=tz,
                )
            return User.objects.get(email=email)
        except IntegrityError:
            return User.objects.get(email=email)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "timezone"]
        read_only_fields = ["id", "email"]

    def validate_timezone(self, value):
        if value not in zoneinfo.available_timezones():
            raise serializers.ValidationError(f"'{value}' is not a valid IANA time zone.")
        return value
