from django.contrib import admin

from apps.coach.models import ChatMessage, PendingAction


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("user__email", "content")
    raw_id_fields = ("user", "pending_action")

    def short_content(self, obj):
        return obj.content[:50]


@admin.register(PendingAction)
class PendingActionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action_type", "status", "expires_at", "created_at")
    list_filter = ("status", "action_type", "created_at")
    search_fields = ("user__email", "summary")
    raw_id_fields = ("user",)
