from datetime import date, timedelta

import pytest
from freezegun import freeze_time

from apps.habits.models import Habit
from apps.habits.services.streaks import StreakResult, calculate_habit_streaks, calculate_streaks


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


def test_calculate_streaks_with_datetime_objects():
    from datetime import datetime

    ref = date(2026, 10, 23)
    checkins = [
        datetime(2026, 10, 23, 10, 30),
        datetime(2026, 10, 22, 18, 0),
    ]
    result = calculate_streaks(checkins, reference_date=ref)
    assert result.current_streak == 2
    assert result.longest_streak == 2


def test_calculate_streaks_with_datetime_reference_date():
    from datetime import datetime

    ref = datetime(2026, 10, 23, 15, 0)
    checkins = [
        datetime(2026, 10, 23, 10, 30),
        datetime(2026, 10, 22, 18, 0),
    ]
    result = calculate_streaks(checkins, reference_date=ref)
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


@freeze_time("2024-03-01")
def test_streak_leap_year_boundary():
    """Verify streaks correctly transition through leap day (Feb 28 -> Feb 29 -> Mar 1)."""
    checkins = [
        date(2024, 2, 28),
        date(2024, 2, 29),
        date(2024, 3, 1),
    ]
    result = calculate_streaks(checkins)
    assert result.current_streak == 3
    assert result.longest_streak == 3


@freeze_time("2024-03-01")
def test_streak_leap_year_missing_leap_day():
    """Missing the leap day (Feb 29) breaks the streak between Feb 28 and Mar 1."""
    checkins = [
        date(2024, 2, 28),
        date(2024, 3, 1),
    ]
    result = calculate_streaks(checkins)
    assert result.current_streak == 1
    assert result.longest_streak == 1


@freeze_time("2025-03-01")
def test_streak_non_leap_year_feb_to_mar():
    """In non-leap year (2025), Feb 28 to Mar 1 are consecutive days."""
    checkins = [
        date(2025, 2, 28),
        date(2025, 3, 1),
    ]
    result = calculate_streaks(checkins)
    assert result.current_streak == 2
    assert result.longest_streak == 2


@freeze_time("2026-01-01")
def test_streak_year_boundary():
    """Verify streaks correctly continue across year boundary (Dec 30 -> Dec 31 -> Jan 1)."""
    checkins = [
        date(2025, 12, 30),
        date(2025, 12, 31),
        date(2026, 1, 1),
    ]
    result = calculate_streaks(checkins)
    assert result.current_streak == 3
    assert result.longest_streak == 3


@freeze_time("2026-01-01")
def test_streak_year_boundary_still_alive_without_today():
    """Check-in on Dec 31 keeps streak alive on Jan 1 even if Jan 1 is not yet checked."""
    checkins = [
        date(2025, 12, 30),
        date(2025, 12, 31),
    ]
    result = calculate_streaks(checkins)
    assert result.current_streak == 2
    assert result.longest_streak == 2


@freeze_time("2026-01-01")
def test_streak_year_boundary_broken():
    """Missing Dec 31 breaks the streak across the year boundary."""
    checkins = [
        date(2025, 12, 30),
        date(2026, 1, 1),
    ]
    result = calculate_streaks(checkins)
    assert result.current_streak == 1
    assert result.longest_streak == 1


# --- Tests for checkin service (Items 4 & 5) ---


def test_validate_checkin_date_accepts_today_and_past():
    from apps.habits.services import validate_checkin_date

    today = date.today()
    past = today - timedelta(days=5)
    # Should not raise
    validate_checkin_date(today)
    validate_checkin_date(past)


def test_validate_checkin_date_rejects_future_date():
    from rest_framework.exceptions import ValidationError

    from apps.habits.services import validate_checkin_date

    future = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError) as exc_info:
        validate_checkin_date(future)
    assert "date" in exc_info.value.detail


def test_validate_checkin_date_respects_user_timezone():
    from unittest.mock import MagicMock

    from rest_framework.exceptions import ValidationError

    from apps.habits.services import validate_checkin_date

    mock_user = MagicMock()
    mock_user.get_today.return_value = date(2026, 10, 23)

    # Date matching user's today should pass
    validate_checkin_date(date(2026, 10, 23), user=mock_user)

    # Date after user's today should fail
    with pytest.raises(ValidationError):
        validate_checkin_date(date(2026, 10, 24), user=mock_user)


@pytest.mark.django_db
def test_check_in_habit_success(habit):
    from apps.habits.models import HabitCheckIn
    from apps.habits.services import CheckInResult, check_in_habit

    today = date.today()
    result = check_in_habit(habit=habit, target_date=today)

    assert isinstance(result, CheckInResult)
    assert result.status == "checked"
    assert result.habit_id == habit.id
    assert result.date == today
    assert result.created is True
    assert result.current_streak == 1
    assert result.longest_streak == 1
    assert HabitCheckIn.objects.filter(habit=habit, date=today).exists()


@pytest.mark.django_db
def test_check_in_habit_idempotent(habit):
    from apps.habits.models import HabitCheckIn
    from apps.habits.services import check_in_habit

    today = date.today()
    res1 = check_in_habit(habit=habit, target_date=today)
    assert res1.created is True

    res2 = check_in_habit(habit=habit, target_date=today)
    assert res2.created is False
    assert res2.status == "checked"
    assert HabitCheckIn.objects.filter(habit=habit, date=today).count() == 1


@pytest.mark.django_db
def test_check_in_habit_handles_integrity_error_concurrent_race(habit, monkeypatch):
    """
    Simulate a race condition where get_or_create raises IntegrityError
    due to another worker inserting the row concurrently.
    Should catch IntegrityError, fetch the existing check-in, and return it with created=False.
    """
    from django.db import IntegrityError

    import apps.habits.services.checkin as checkin_service
    from apps.habits.models import HabitCheckIn
    from apps.habits.services import check_in_habit

    today = date.today()
    # Existing check-in in DB (simulating concurrent worker inserted it)
    HabitCheckIn.objects.create(habit=habit, date=today)

    def mock_get_or_create(*args, **kwargs):
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr(checkin_service.HabitCheckIn.objects, "get_or_create", mock_get_or_create)

    result = check_in_habit(habit=habit, target_date=today)
    assert result.status == "checked"
    assert result.habit_id == habit.id
    assert result.date == today
    assert result.created is False
    assert result.current_streak == 1


@pytest.mark.django_db
def test_check_in_habit_rejects_archived(habit):
    from rest_framework.exceptions import ValidationError

    from apps.habits.services import check_in_habit

    habit.is_archived = True
    habit.save()

    with pytest.raises(ValidationError) as exc_info:
        check_in_habit(habit=habit)
    assert "detail" in exc_info.value.detail or "Cannot check in on an archived habit." in str(
        exc_info.value
    )


@pytest.mark.django_db
def test_check_in_and_uncheck_habit_with_prefetched_cache(habit):
    """
    Ensure check_in_habit and uncheck_habit return fresh streak calculations
    even if the habit instance has a populated _prefetched_objects_cache.
    """
    from apps.habits.models import Habit
    from apps.habits.services import check_in_habit, uncheck_habit

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Populate yesterday checkin
    habit.check_ins.create(date=yesterday)

    # Fetch habit with prefetch
    prefetched_habit = Habit.objects.prefetch_related("check_ins").get(id=habit.id)
    assert len(prefetched_habit.check_ins.all()) == 1

    # Check in today using the prefetched instance
    res_check = check_in_habit(habit=prefetched_habit, target_date=today)
    assert res_check.current_streak == 2
    assert res_check.longest_streak == 2

    # Uncheck today using the same instance
    res_uncheck = uncheck_habit(habit=prefetched_habit, target_date=today)
    assert res_uncheck.current_streak == 1
    assert res_uncheck.longest_streak == 1


@pytest.mark.django_db
def test_uncheck_habit_nonexistent_raises_not_found(habit):
    from rest_framework.exceptions import NotFound

    from apps.habits.services import uncheck_habit

    with pytest.raises(NotFound):
        uncheck_habit(habit=habit, target_date=date.today())


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_recalculate_habit_streaks_service(habit):
    from apps.habits.services import recalculate_habit_streaks

    today = date(2026, 10, 23)
    yesterday = date(2026, 10, 22)

    # Habit with no check-ins
    recalculate_habit_streaks(habit)
    habit.refresh_from_db()
    assert habit.current_streak == 0
    assert habit.longest_streak == 0
    assert habit.last_check_in_date is None

    # Add check-ins directly bypassing signals/services to verify recalculate
    habit.check_ins.bulk_create(
        [
            habit.check_ins.model(habit=habit, date=yesterday),
            habit.check_ins.model(habit=habit, date=today),
        ]
    )
    # Manually reset to 0 to simulate un-recalculated state
    habit.current_streak = 0
    habit.longest_streak = 0
    habit.last_check_in_date = None
    habit.save()

    recalculate_habit_streaks(habit)
    habit.refresh_from_db()
    assert habit.current_streak == 2
    assert habit.longest_streak == 2
    assert habit.last_check_in_date == today


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_habit_get_current_streak_read_time_decay(habit, django_assert_num_queries):
    """
    Current streak must become 0 when days pass without check-ins.
    Handled at read time using last_check_in_date and the user's today without loading check-ins.
    """
    today = date(2026, 10, 23)
    yesterday = date(2026, 10, 22)
    two_days_ago = date(2026, 10, 21)

    # 1. Checked today: streak is alive
    habit.current_streak = 5
    habit.longest_streak = 10
    habit.last_check_in_date = today
    habit.save()

    with django_assert_num_queries(0):
        assert habit.get_current_streak(reference_date=today) == 5

    # 2. Checked yesterday: streak is alive
    habit.last_check_in_date = yesterday
    habit.save()

    with django_assert_num_queries(0):
        assert habit.get_current_streak(reference_date=today) == 5

    # 3. Checked 2 days ago: streak has lapsed to 0
    habit.last_check_in_date = two_days_ago
    habit.save()

    with django_assert_num_queries(0):
        assert habit.get_current_streak(reference_date=today) == 0

    # Stored current_streak in DB was not modified
    habit.refresh_from_db()
    assert habit.current_streak == 5


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_recalculate_streaks_management_command(user):
    from io import StringIO

    from django.core.management import call_command

    from apps.habits.models import Habit

    today = date(2026, 10, 23)
    yesterday = date(2026, 10, 22)

    h1 = Habit.objects.create(user=user, name="Habit 1")
    h2 = Habit.objects.create(user=user, name="Habit 2")

    # Insert checkins via bulk_create so signals don't fire
    h1.check_ins.model.objects.bulk_create(
        [
            h1.check_ins.model(habit=h1, date=yesterday),
            h1.check_ins.model(habit=h1, date=today),
        ]
    )
    h2.check_ins.model.objects.bulk_create(
        [
            h2.check_ins.model(habit=h2, date=yesterday),
        ]
    )

    h1.refresh_from_db()
    h2.refresh_from_db()
    assert h1.current_streak == 0
    assert h2.current_streak == 0

    out = StringIO()
    call_command("recalculate_streaks", stdout=out)
    assert "Successfully recalculated streaks for 2 habit(s)" in out.getvalue()

    h1.refresh_from_db()
    h2.refresh_from_db()
    assert h1.current_streak == 2
    assert h1.longest_streak == 2
    assert h1.last_check_in_date == today
    assert h2.current_streak == 1
    assert h2.longest_streak == 1
    assert h2.last_check_in_date == yesterday

    # Test filtering with --habit-id
    out_filtered = StringIO()
    call_command("recalculate_streaks", habit_id=h1.id, stdout=out_filtered)
    assert "Successfully recalculated streaks for 1 habit(s)" in out_filtered.getvalue()

    # Test filtering with --user-id
    out_user = StringIO()
    call_command("recalculate_streaks", user_id=user.id, stdout=out_user)
    assert "Successfully recalculated streaks for 2 habit(s)" in out_user.getvalue()
