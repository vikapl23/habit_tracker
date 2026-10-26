from datetime import date, timedelta

import pytest
from freezegun import freeze_time

from apps.habits.models import Habit
from apps.habits.services.statistics import (
    calculate_habit_statistics,
    calculate_user_summary_statistics,
    is_day_completed,
)


@pytest.mark.django_db
class TestHabitStatisticsService:
    @freeze_time("2026-10-26 12:00:00")
    def test_habit_statistics_empty_history(self, user):
        # Habit created 10 days ago, no check-ins
        habit = Habit.objects.create(
            user=user,
            name="Read Book",
            frequency_type="daily",
        )
        # Manually backdate created_at
        Habit.objects.filter(pk=habit.pk).update(created_at=user.get_today() - timedelta(days=10))
        habit.refresh_from_db()

        stats = calculate_habit_statistics(habit, user=user)

        assert stats["completion_rate_7d"] == 0.0
        assert stats["completion_rate_30d"] == 0.0
        assert stats["total_check_ins"] == 0
        assert stats["current_streak"] == 0
        assert stats["longest_streak"] == 0

    @freeze_time("2026-10-26 12:00:00")
    def test_habit_statistics_days_before_creation_do_not_count(self, user):
        # Habit created 3 days ago (today - 2 days): exactly 3 days: today-2, today-1, today
        today = user.get_today()
        habit = Habit.objects.create(
            user=user,
            name="Meditate",
            frequency_type="daily",
        )
        Habit.objects.filter(pk=habit.pk).update(created_at=today - timedelta(days=2))
        habit.refresh_from_db()

        # Check-in on today and today - 1
        habit.check_ins.create(date=today)
        habit.check_ins.create(date=today - timedelta(days=1))
        # Recalculate streak
        from apps.habits.services.streaks import recalculate_habit_streaks

        recalculate_habit_streaks(habit, reference_date=today)
        habit.refresh_from_db()

        stats = calculate_habit_statistics(habit, user=user)

        # Scheduled days in last 7 days window: only 3 days because created 3 days ago
        # Completed days: 2
        # Completion rate: 2 / 3 = 0.6667 (66.7%)
        assert stats["completion_rate_7d"] == round(2 / 3, 4)
        assert stats["completion_rate_30d"] == round(2 / 3, 4)
        assert stats["total_check_ins"] == 2
        assert stats["current_streak"] == 2
        assert stats["longest_streak"] == 2

    @freeze_time("2026-10-26 12:00:00")
    def test_habit_statistics_with_custom_frequency(self, user):
        # Habit scheduled on Mon(0), Wed(2), Fri(4)
        # 2026-10-26 is Monday (weekday 0)
        today = user.get_today()
        assert today.weekday() == 0  # Monday

        habit = Habit.objects.create(
            user=user,
            name="Gym",
            frequency_type="custom",
            frequency_days=[0, 2, 4],
        )
        # Created 14 days ago
        Habit.objects.filter(pk=habit.pk).update(created_at=today - timedelta(days=14))
        habit.refresh_from_db()

        # In last 7 days (today - 6 to today inclusive):
        # Days: Tue(1), Wed(2), Thu(3), Fri(4), Sat(5), Sun(6), Mon(0)
        # Scheduled: Wed, Fri, Mon -> 3 scheduled days
        # Check-in on Wed and Mon
        habit.check_ins.create(date=today - timedelta(days=5))  # Wed
        habit.check_ins.create(date=today)  # Mon
        from apps.habits.services.streaks import recalculate_habit_streaks

        recalculate_habit_streaks(habit, reference_date=today)
        habit.refresh_from_db()

        stats = calculate_habit_statistics(habit, user=user)

        assert stats["completion_rate_7d"] == round(2 / 3, 4)
        assert stats["total_check_ins"] == 2


@pytest.mark.django_db
class TestUserSummaryStatisticsService:
    @freeze_time("2026-10-26 12:00:00")
    def test_summary_empty_habits(self, user):
        summary = calculate_user_summary_statistics(user)
        assert summary["overall_completion_rate_week"] == 0.0
        assert summary["overall_completion_rate_month"] == 0.0
        assert summary["best_habit"] is None
        assert summary["total_active_habits"] == 0
        assert summary["total_check_ins"] == 0

    @freeze_time("2026-10-26 12:00:00")
    def test_summary_with_habits(self, user, other_user):
        today = user.get_today()
        # Create 2 active habits for user, 1 archived habit, 1 habit for other_user
        h1 = Habit.objects.create(user=user, name="Water", frequency_type="daily")
        h2 = Habit.objects.create(user=user, name="Running", frequency_type="daily")
        Habit.objects.create(user=user, name="Old", is_archived=True)
        Habit.objects.create(user=other_user, name="Other", frequency_type="daily")

        # Backdate created_at to beginning of month (e.g. 2026-10-01)
        start_of_month = today.replace(day=1)
        Habit.objects.filter(user=user).update(created_at=start_of_month)
        h1.refresh_from_db()
        h2.refresh_from_db()

        # Check-ins for h1: all days this week (Monday today, so this week starts Monday 2026-10-26)
        # Wait, if today is Monday, this week has 1 day elapsed so far: Monday
        h1.check_ins.create(date=today)

        summary = calculate_user_summary_statistics(user)
        assert summary["total_active_habits"] == 2
        assert summary["total_check_ins"] == 1
        assert summary["best_habit"] is not None
        assert summary["best_habit"]["id"] == h1.id
        assert summary["best_habit"]["name"] == "Water"


def test_is_day_completed_helper():
    checkin_dates = {date(2026, 10, 26), date(2026, 10, 25)}
    assert is_day_completed(date(2026, 10, 26), checkin_dates) is True
    assert is_day_completed(date(2026, 10, 24), checkin_dates) is False
