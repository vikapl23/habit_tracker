import pytest
from datetime import date, timedelta
from freezegun import freeze_time
from apps.habits.models import Habit, HabitCheckIn
from apps.habits.services.streaks import calculate_streaks, calculate_habit_streaks, StreakResult


@freeze_time("2026-10-23")
def test_streak_no_check_ins():
    """No check-ins at all: current and longest streak should both be 0."""
    result = calculate_streaks([])
    assert isinstance(result, StreakResult)
    assert result.current_streak == 0
    assert result.longest_streak == 0
    # Also test tuple unpacking
    current, longest = result
    assert current == 0
    assert longest == 0


@freeze_time("2026-10-23")
def test_streak_only_today():
    """Only today is checked in: current streak 1, longest streak 1."""
    today = date(2026, 10, 23)
    result = calculate_streaks([today])
    assert result.current_streak == 1
    assert result.longest_streak == 1


@freeze_time("2026-10-23")
def test_streak_only_yesterday():
    """
    Only yesterday is checked in:
    Since today is not checked yet, but yesterday is, the streak is still alive!
    current streak 1, longest streak 1.
    """
    yesterday = date(2026, 10, 22)
    result = calculate_streaks([yesterday])
    assert result.current_streak == 1
    assert result.longest_streak == 1


@freeze_time("2026-10-23")
def test_streak_two_days_ago_broken():
    """
    Check-in was 2 days ago (yesterday was missed):
    Streak has lapsed; current streak 0, longest streak 1.
    """
    two_days_ago = date(2026, 10, 21)
    result = calculate_streaks([two_days_ago])
    assert result.current_streak == 0
    assert result.longest_streak == 1


@freeze_time("2026-10-23")
def test_streak_consecutive_active_multi_day():
    """Check-ins on today, yesterday, and 2 days ago: current 3, longest 3."""
    today = date(2026, 10, 23)
    dates = [today - timedelta(days=i) for i in range(3)]
    result = calculate_streaks(dates)
    assert result.current_streak == 3
    assert result.longest_streak == 3


@freeze_time("2026-10-23")
def test_streak_consecutive_ending_yesterday_multi_day():
    """
    Check-ins on yesterday, 2 days ago, and 3 days ago (today not checked yet):
    Streak is still alive; current 3, longest 3.
    """
    yesterday = date(2026, 10, 22)
    dates = [yesterday - timedelta(days=i) for i in range(3)]
    result = calculate_streaks(dates)
    assert result.current_streak == 3
    assert result.longest_streak == 3


@freeze_time("2026-10-23")
def test_streak_gap_in_the_middle():
    """
    Check-in history with a gap in the middle:
    e.g. today and yesterday (2 days), gap on 2 days ago,
    then 3 days ago and 4 days ago (2 days).
    Current streak is 2, longest streak is 2.
    """
    today = date(2026, 10, 23)
    dates = [
        today,
        today - timedelta(days=1),  # Oct 22
        # Oct 21 missed (gap)
        today - timedelta(days=3),  # Oct 20
        today - timedelta(days=4),  # Oct 19
    ]
    result = calculate_streaks(dates)
    assert result.current_streak == 2
    assert result.longest_streak == 2


@freeze_time("2026-10-23")
def test_streak_longest_in_past_bigger_than_current():
    """
    Past streak was 5 days, then a gap, then 2 days ending today.
    Current streak should be 2, longest streak should be 5.
    """
    today = date(2026, 10, 23)
    # Past 5-day streak: Oct 10 to Oct 14
    past_dates = [date(2026, 10, 10) + timedelta(days=i) for i in range(5)]
    # Current 2-day streak: Oct 22, Oct 23
    current_dates = [today - timedelta(days=1), today]
    result = calculate_streaks(past_dates + current_dates)
    assert result.current_streak == 2
    assert result.longest_streak == 5


@freeze_time("2026-10-23")
def test_streak_undo_breaks_the_streak():
    """
    Removing/undoing check-ins alters the streak accordingly:
    1. 3 consecutive days ending today: current=3, longest=3.
    2. Undo today's check-in: yesterday is now the latest; current=2, longest=3 (or 2 if history had no other).
    3. Undo yesterday's check-in: only 2 days ago remains; current lapses to 0, longest=1.
    4. Undoing an intermediate day splits a streak.
    """
    today = date(2026, 10, 23)
    day_minus_1 = today - timedelta(days=1)
    day_minus_2 = today - timedelta(days=2)

    # Initial: 3 days streak
    all_three = [day_minus_2, day_minus_1, today]
    res1 = calculate_streaks(all_three)
    assert res1.current_streak == 3
    assert res1.longest_streak == 3

    # Undo today
    without_today = [day_minus_2, day_minus_1]
    res2 = calculate_streaks(without_today)
    assert res2.current_streak == 2
    assert res2.longest_streak == 2

    # Undo yesterday as well: only 2 days ago remains
    without_yesterday = [day_minus_2]
    res3 = calculate_streaks(without_yesterday)
    assert res3.current_streak == 0
    assert res3.longest_streak == 1

    # Undoing the middle day (day_minus_1) leaves today and day_minus_2
    middle_undone = [day_minus_2, today]
    res4 = calculate_streaks(middle_undone)
    assert res4.current_streak == 1
    assert res4.longest_streak == 1


@freeze_time("2026-10-23")
def test_streak_unordered_and_duplicate_dates():
    """Deduplication and out-of-order check-in dates work seamlessly."""
    today = date(2026, 10, 23)
    yesterday = date(2026, 10, 22)
    # Duplicates and unsorted
    dates = [today, yesterday, today, yesterday, today]
    result = calculate_streaks(dates)
    assert result.current_streak == 2
    assert result.longest_streak == 2


@freeze_time("2026-10-23")
def test_streak_explicit_reference_date():
    """Passing a custom reference date calculates streaks relative to that date."""
    ref_date = date(2026, 5, 10)
    checkin_dates = [date(2026, 5, 9), date(2026, 5, 10)]
    result = calculate_streaks(checkin_dates, reference_date=ref_date)
    assert result.current_streak == 2
    assert result.longest_streak == 2


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_calculate_habit_streaks_integration(habit):
    """Test calculate_habit_streaks directly on a Habit model instance."""
    today = date(2026, 10, 23)
    yesterday = date(2026, 10, 22)

    # Empty habit
    result = calculate_habit_streaks(habit)
    assert result.current_streak == 0
    assert result.longest_streak == 0

    # Add yesterday checkin
    habit.check_ins.create(date=yesterday)
    result = calculate_habit_streaks(habit)
    assert result.current_streak == 1
    assert result.longest_streak == 1

    # Add today checkin
    habit.check_ins.create(date=today)
    result = calculate_habit_streaks(habit)
    assert result.current_streak == 2
    assert result.longest_streak == 2


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_habit_serializer_computes_streaks(habit):
    """Verify that HabitSerializer includes computed current_streak and longest_streak."""
    from apps.habits.serializers import HabitSerializer
    today = date(2026, 10, 23)
    yesterday = date(2026, 10, 22)

    serializer_empty = HabitSerializer(habit)
    assert serializer_empty.data["current_streak"] == 0
    assert serializer_empty.data["longest_streak"] == 0

    habit.check_ins.create(date=yesterday)
    # Clear cached streaks on instance if any
    habit = Habit.objects.get(id=habit.id)
    serializer_yesterday = HabitSerializer(habit)
    assert serializer_yesterday.data["current_streak"] == 1
    assert serializer_yesterday.data["longest_streak"] == 1

    habit.check_ins.create(date=today)
    habit = Habit.objects.get(id=habit.id)
    serializer_today = HabitSerializer(habit)
    assert serializer_today.data["current_streak"] == 2
    assert serializer_today.data["longest_streak"] == 2

