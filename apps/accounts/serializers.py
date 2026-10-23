from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

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
        try:
            if not User.objects.filter(email=email).exists():
                return User.objects.create_user(email=email, password=validated_data["password"])
            return User.objects.get(email=email)
        except IntegrityError:
            return User.objects.get(email=email)
