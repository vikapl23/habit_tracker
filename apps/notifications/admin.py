from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_email", "habit", "notification_type", "scheduled_date", "sent_at")
    list_filter = ("notification_type", "scheduled_date")
    search_fields = ("recipient_email", "user__email", "habit__name")
    readonly_fields = (
        "user",
        "habit",
        "notification_type",
        "scheduled_date",
        "recipient_email",
        "sent_at",
        "details",
    )
