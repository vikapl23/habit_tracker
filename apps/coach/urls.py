from django.urls import path

from apps.coach.views import CoachMessagesView

app_name = "coach"

urlpatterns = [
    path("messages/", CoachMessagesView.as_view(), name="coach-messages"),
]
