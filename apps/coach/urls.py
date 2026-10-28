from django.urls import path

from apps.coach.views import (
    CoachActionCancelView,
    CoachActionConfirmView,
    CoachMessagesView,
)

app_name = "coach"

urlpatterns = [
    path("messages/", CoachMessagesView.as_view(), name="coach-messages"),
    path(
        "actions/<int:pk>/confirm/",
        CoachActionConfirmView.as_view(),
        name="coach-action-confirm",
    ),
    path(
        "actions/<int:pk>/cancel/",
        CoachActionCancelView.as_view(),
        name="coach-action-cancel",
    ),
]
