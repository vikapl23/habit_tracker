from __future__ import annotations

import zoneinfo
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """Serializer for registering a new user with email, password, and timezone."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    timezone = serializers.CharField(required=False, default="Europe/Kyiv")

    def validate_timezone(self, value: str) -> str:
        """Validate timezone, falling back to UTC if invalid during registration."""
        if not value:
            return "UTC"
        try:
            zoneinfo.ZoneInfo(value)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            return "UTC"
        if value == "Europe/Kiev":
            return "Europe/Kyiv"
        return value

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """Normalize email to lowercase before validation."""
        if hasattr(data, "copy"):
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)
        if isinstance(data, dict) and "email" in data and isinstance(data["email"], str):
            data["email"] = data["email"].lower()
        return super().to_internal_value(data)

    def create(self, validated_data: dict[str, Any]) -> AbstractBaseUser:
        """Create a user with lowercased email or return existing user if already registered."""
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
    """Serializer for retrieving and updating user profile details."""

    class Meta:
        model = User
        fields = ["id", "email", "timezone"]
        read_only_fields = ["id", "email"]

    def validate_timezone(self, value: str) -> str:
        """Validate that the provided timezone is a recognized IANA time zone."""
        if not value:
            raise serializers.ValidationError("Timezone cannot be empty.")
        try:
            zoneinfo.ZoneInfo(value)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError) as err:
            raise serializers.ValidationError(f"'{value}' is not a valid IANA time zone.") from err
        if value == "Europe/Kiev":
            return "Europe/Kyiv"
        return value
