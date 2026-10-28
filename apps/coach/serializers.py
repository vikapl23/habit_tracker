from rest_framework import serializers

from apps.coach.models import ChatMessage, PendingAction


class PendingActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingAction
        fields = (
            "id",
            "action_type",
            "summary",
            "status",
            "expires_at",
            "payload",
        )
        read_only_fields = fields


class ChatMessageSerializer(serializers.ModelSerializer):
    pending_action = PendingActionSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = (
            "id",
            "role",
            "content",
            "pending_action",
            "created_at",
        )
        read_only_fields = fields


class CoachMessageInputSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=1000,
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate_content(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Message content cannot be blank.")
        return stripped
