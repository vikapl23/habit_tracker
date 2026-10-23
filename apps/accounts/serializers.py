from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password")
        read_only_fields = ("id",)

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)
        if isinstance(data, dict) and "email" in data and isinstance(data["email"], str):
            data["email"] = data["email"].lower()
        return super().to_internal_value(data)

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"], password=validated_data["password"]
        )
