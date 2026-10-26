from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import HabitViewSet, StatisticsSummaryView

router = DefaultRouter()
router.register("habits", HabitViewSet, basename="habit")

urlpatterns = [
    path("statistics/summary/", StatisticsSummaryView.as_view(), name="statistics-summary"),
] + router.urls
