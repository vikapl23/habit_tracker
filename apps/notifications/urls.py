from django.urls import path

from apps.notifications.views import SendNotificationsInternalView, UnsubscribeView

urlpatterns = [
    path(
        "internal/send-notifications/",
        SendNotificationsInternalView.as_view(),
        name="internal-send-notifications",
    ),
    path(
        "notifications/unsubscribe/<str:token>/",
        UnsubscribeView.as_view(),
        name="notification-unsubscribe",
    ),
]
