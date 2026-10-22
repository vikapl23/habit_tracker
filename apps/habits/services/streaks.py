from datetime import date, timedelta
from typing import Iterable, Tuple, Optional
from django.utils import timezone

def calculate_streaks(checkin_dates: Iterable[date], reference_date: Optional[date] = None) -> Tuple[int, int]:
    """
    Calculates current streak and longest streak from a collection of check-in dates.
    
    :param checkin_dates: Iterable of date objects representing completed check-ins.
    :param reference_date: The reference 'today' date. Defaults to current local date.
    :return: (current_streak, longest_streak) tuple of integers.
    """
    if reference_date is None:
        reference_date = timezone.localdate()

    dates_set = set(checkin_dates)
    if not dates_set:
        return 0, 0

    yesterday = reference_date - timedelta(days=1)

    # 1. Current streak calculation
    if reference_date in dates_set:
        cursor = reference_date
    elif yesterday in dates_set:
        cursor = yesterday
    else:
        cursor = None

    current_streak = 0
    if cursor is not None:
        while cursor in dates_set:
            current_streak += 1
            cursor -= timedelta(days=1)

    # 2. Longest streak calculation
    sorted_dates = sorted(dates_set)
    max_streak = 1
    curr_streak = 1

    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] == sorted_dates[i - 1] + timedelta(days=1):
            curr_streak += 1
        elif sorted_dates[i] == sorted_dates[i - 1]:
            continue
        else:
            curr_streak = 1

        if curr_streak > max_streak:
            max_streak = curr_streak

    return current_streak, max_streak
