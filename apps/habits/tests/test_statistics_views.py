from datetime import datetime, time, timedelta

import pytest
from freezegun import freeze_time
from rest_framework import status

from apps.habits.models import Habit


@pytest.mark.django_db
class TestStatisticsViews:
    @freeze_time("2026-10-26 12:00:00")
    def test_habit_statistics_endpoint_success(self, api_client, user):
        today = user.get_today()
        # Create habit created 10 days ago
        created_time = datetime.combine(today - timedelta(days=10), time(12, 0))
        habit = Habit.objects.create(
            user=user,
            name="Reading",
            frequency_type="daily",
        )
        Habit.objects.filter(pk=habit.pk).update(created_at=created_time)
        habit.refresh_from_db()

        # Check-in on today and yesterday
        habit.check_ins.create(date=today)
        habit.check_ins.create(date=today - timedelta(days=1))
        from apps.habits.services.streaks import recalculate_habit_streaks

        recalculate_habit_streaks(habit, reference_date=today)
        habit.refresh_from_db()

        response = api_client.get(f"/api/v1/habits/{habit.id}/statistics/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["habit_id"] == habit.id
        # In last 7 days: 2 completed out of 7 scheduled
        assert data["completion_rate_7d"] == round(2 / 7, 4)
        # In last 30 days: 2 completed out of 11 scheduled (10 days ago to today = 11 days)
        assert data["completion_rate_30d"] == round(2 / 11, 4)
        assert data["total_check_ins"] == 2
        assert data["current_streak"] == 2
        assert data["longest_streak"] == 2

    @freeze_time("2026-10-26 12:00:00")
    def test_habit_statistics_other_user_404(self, api_client, other_user):
        other_habit = Habit.objects.create(user=other_user, name="Secret Habit")
        response = api_client.get(f"/api/v1/habits/{other_habit.id}/statistics/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @freeze_time("2026-10-26 12:00:00")
    def test_habit_statistics_unauthenticated_401(self, unauthenticated_client, habit):
        response = unauthenticated_client.get(f"/api/v1/habits/{habit.id}/statistics/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @freeze_time("2026-10-26 12:00:00")
    def test_summary_statistics_endpoint_success(self, api_client, user, other_user):
        today = user.get_today()
        created_time = datetime.combine(today - timedelta(days=20), time(12, 0))

        # Habit 1: checked in today
        h1 = Habit.objects.create(user=user, name="Water", frequency_type="daily")
        Habit.objects.filter(pk=h1.pk).update(created_at=created_time)
        h1.check_ins.create(date=today)

        # Habit 2: no check-ins
        h2 = Habit.objects.create(user=user, name="Gym", frequency_type="daily")
        Habit.objects.filter(pk=h2.pk).update(created_at=created_time)

        # Other user's habit: check-in should not be counted
        h_other = Habit.objects.create(user=other_user, name="Other", frequency_type="daily")
        h_other.check_ins.create(date=today)

        response = api_client.get("/api/v1/statistics/summary/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["total_active_habits"] == 2
        assert data["total_check_ins"] == 1
        assert data["best_habit"]["id"] == h1.id
        assert data["best_habit"]["name"] == "Water"
        assert data["overall_completion_rate_week"] > 0
        assert data["overall_completion_rate_month"] > 0

    @freeze_time("2026-10-26 12:00:00")
    def test_summary_statistics_unauthenticated_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/v1/statistics/summary/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @freeze_time("2026-10-26 12:00:00")
    def test_summary_statistics_query_count_no_n_plus_one(
        self, api_client, user, django_assert_num_queries
    ):
        today = user.get_today()
        created_time = datetime.combine(today - timedelta(days=15), time(12, 0))

        # Create 10 habits with various check-ins
        for i in range(10):
            h = Habit.objects.create(user=user, name=f"Habit {i}", frequency_type="daily")
            Habit.objects.filter(pk=h.pk).update(created_at=created_time)
            h.check_ins.create(date=today)

        # Let's count queries:
        # 1. user lookup / auth session
        # 2. list active habits
        # 3. count total check-ins across user habits
        # 4. fetch relevant check-ins for active habits in the date range
        # Total should remain constant regardless of whether there are 2 or 10 habits!
        with django_assert_num_queries(3):
            response = api_client.get("/api/v1/statistics/summary/")
            assert response.status_code == status.HTTP_200_OK
            assert response.data["total_active_habits"] == 10
            assert response.data["total_check_ins"] == 10
