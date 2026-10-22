import pytest
from datetime import date, timedelta
from apps.habits.services.streaks import calculate_streaks

@pytest.mark.parametrize("checked_offsets,expected_current,expected_longest", [
    ([], 0, 0),                           # No check-ins
    ([0], 1, 1),                          # Checked today
    ([-1], 1, 1),                         # Checked yesterday (unbroken)
    ([-2], 0, 1),                         # Checked 2 days ago (broken)
    ([0, -1, -2], 3, 3),                  # 3-day active streak through today
    ([-1, -2, -3], 3, 3),                 # 3-day streak ending yesterday
    ([-10, -9, -8, -1, 0], 2, 3),         # Past 3-day streak, current 2-day streak
    ([-7, -6, -5, -4, -2, -1, 0], 3, 4),  # Gap in past: 4-day past streak, 3-day current
])
def test_streak_calculation_scenarios(checked_offsets, expected_current, expected_longest):
    today = date(2026, 10, 22)
    checkin_dates = {today + timedelta(days=offset) for offset in checked_offsets}
    current_streak, longest_streak = calculate_streaks(checkin_dates, reference_date=today)
    assert current_streak == expected_current
    assert longest_streak == expected_longest


def test_streak_calculation_empty():
    current, longest = calculate_streaks(set(), reference_date=date(2026, 10, 22))
    assert current == 0
    assert longest == 0


def test_streak_calculation_default_reference_date():
    today = date.today()
    checkin_dates = {today}
    current, longest = calculate_streaks(checkin_dates)
    assert current == 1
    assert longest == 1
