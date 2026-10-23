from datetime import date, timedelta

import pytest
from freezegun import freeze_time
from rest_framework import status

from apps.habits.models import Habit


@pytest.mark.django_db
def test_list_habits(api_client, habit):
    Habit.objects.create(user=habit.user, name="Archived Habit", is_archived=True)

    # By default, archived habits should not be listed
    response = api_client.get("/api/v1/habits/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == habit.id

    # With include_archived=true
    response = api_client.get("/api/v1/habits/?include_archived=true")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_list_habits_query_count_constant(api_client, user, django_assert_num_queries):
    today = date.today()
    for i in range(5):
        h = Habit.objects.create(user=user, name=f"Habit {i}")
        h.check_ins.create(date=today)

    # 1 query for count + 1 query to fetch habits (check-ins are not loaded) = 2 queries
    with django_assert_num_queries(2):
        response = api_client.get("/api/v1/habits/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 5
        assert len(response.data["results"]) == 5


@pytest.mark.django_db
def test_list_habits_does_not_load_checkins(api_client, user, django_assert_num_queries):
    """
    Mentor Review item 6: Prove that the habits list view does not load check-ins.
    Streaks and today's status are evaluated from fields on Habit and the user's today date.
    """
    today = date.today()
    for i in range(5):
        habit = Habit.objects.create(user=user, name=f"Habit {i}")
        for day_offset in range(10):
            habit.check_ins.create(date=today - timedelta(days=day_offset))

    # Exactly 2 queries: 1 count + 1 select habits. ZERO check-in queries.
    with django_assert_num_queries(2) as ctx:
        res = api_client.get("/api/v1/habits/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] == 5
        assert len(res.data["results"]) == 5

    # Verify that habits_habitcheckin table is never queried
    for query in ctx.captured_queries:
        assert "habitcheckin" not in query["sql"].lower()


@pytest.mark.django_db
def test_create_habit(api_client):
    payload = {
        "name": "Morning Meditation",
        "description": "10 minutes of mindfulness",
        "color": "#10B981",
        "emoji": "🧘",
    }
    response = api_client.post("/api/v1/habits/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Morning Meditation"
    assert response.data["color"] == "#10B981"
    assert response.data["emoji"] == "🧘"
    assert response.data["is_archived"] is False
    assert response.data["current_streak"] == 0
    assert response.data["longest_streak"] == 0


@pytest.mark.django_db
def test_create_habit_validation_error(api_client):
    response = api_client.post("/api/v1/habits/", {"name": ""}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "name" in response.data


@pytest.mark.django_db
def test_retrieve_habit(api_client, habit):
    response = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == habit.id
    assert response.data["name"] == habit.name


@pytest.mark.django_db
def test_update_habit(api_client, habit):
    payload = {
        "name": "Updated Water Habit",
        "description": "Drink 3 liters",
        "color": "#000000",
        "emoji": "🚰",
    }
    response = api_client.put(f"/api/v1/habits/{habit.id}/", payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    habit.refresh_from_db()
    assert habit.name == "Updated Water Habit"


@pytest.mark.django_db
def test_partial_update_habit(api_client, habit):
    response = api_client.patch(f"/api/v1/habits/{habit.id}/", {"name": "New Name"}, format="json")
    assert response.status_code == status.HTTP_200_OK
    habit.refresh_from_db()
    assert habit.name == "New Name"


@pytest.mark.django_db
def test_delete_habit(api_client, habit):
    response = api_client.delete(f"/api/v1/habits/{habit.id}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Habit.objects.filter(id=habit.id).exists()


@pytest.mark.django_db
def test_archive_and_unarchive_habit(api_client, habit):
    # Archive
    response = api_client.post(f"/api/v1/habits/{habit.id}/archive/")
    assert response.status_code == status.HTTP_200_OK
    habit.refresh_from_db()
    assert habit.is_archived is True

    # Unarchive
    response = api_client.post(f"/api/v1/habits/{habit.id}/unarchive/")
    assert response.status_code == status.HTTP_200_OK
    habit.refresh_from_db()
    assert habit.is_archived is False


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_check_in_on_archived_habit_returns_400(api_client, user):
    archived_habit = Habit.objects.create(user=user, name="Archived Habit", is_archived=True)
    res = api_client.post(f"/api/v1/habits/{archived_habit.id}/check/", {})
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in res.data
    assert res.data["detail"] == "Cannot check in on an archived habit."


# ---------------------------------------------------------------------------
# MVP Step 2: CheckIn API Tests (Mark done, Undo, List check-ins, Rules)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_check_in_default_today(api_client, habit):
    today = date.today()
    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "checked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == str(today)
    assert habit.check_ins.filter(date=today).exists()


@pytest.mark.django_db
@freeze_time("2026-10-23T22:30:00Z")
def test_check_in_default_today_kyiv_timezone(api_client, habit):
    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "checked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == "2026-10-24"
    assert habit.check_ins.filter(date=date(2026, 10, 24)).exists()


@pytest.mark.django_db
def test_check_in_explicit_date(api_client, habit):
    past_date = date.today() - timedelta(days=2)
    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(past_date)})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "checked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == str(past_date)
    assert habit.check_ins.filter(date=past_date).exists()


@pytest.mark.django_db
def test_check_in_idempotency(api_client, habit):
    today = date.today()
    res1 = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(today)})
    assert res1.status_code == status.HTTP_201_CREATED

    # Second check-in on the same date should be idempotent (200 OK, no duplicate)
    res2 = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(today)})
    assert res2.status_code == status.HTTP_200_OK
    assert res2.data["status"] == "checked"
    assert habit.check_ins.filter(date=today).count() == 1


@pytest.mark.django_db
def test_cannot_check_in_future_date(api_client, habit):
    future_date = date.today() + timedelta(days=1)
    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(future_date)})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "date" in response.data


@pytest.mark.django_db
def test_check_in_nonexistent_habit_404(api_client):
    response = api_client.post("/api/v1/habits/99999/check/", {})
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_uncheck_existing_checkin(api_client, habit):
    today = date.today()
    habit.check_ins.create(date=today)
    response = api_client.post(f"/api/v1/habits/{habit.id}/uncheck/", {"date": str(today)})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "unchecked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == str(today)
    assert not habit.check_ins.filter(date=today).exists()


@pytest.mark.django_db
def test_uncheck_default_today(api_client, habit):
    today = date.today()
    habit.check_ins.create(date=today)
    response = api_client.post(f"/api/v1/habits/{habit.id}/uncheck/", {})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "unchecked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == str(today)
    assert not habit.check_ins.filter(date=today).exists()


@pytest.mark.django_db
def test_uncheck_nonexistent_checkin_404(api_client, habit):
    today = date.today()
    response = api_client.post(f"/api/v1/habits/{habit.id}/uncheck/", {"date": str(today)})
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_uncheck_nonexistent_habit_404(api_client):
    response = api_client.post("/api/v1/habits/99999/uncheck/", {})
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_list_checkins(api_client, habit):
    today = date.today()
    yesterday = today - timedelta(days=1)
    habit.check_ins.create(date=yesterday)
    habit.check_ins.create(date=today)

    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    dates = [item["date"] for item in response.data["results"]]
    assert str(today) in dates
    assert str(yesterday) in dates


@pytest.mark.django_db
def test_list_checkins_date_range_filter(api_client, habit):
    today = date.today()
    d1 = today - timedelta(days=5)
    d2 = today - timedelta(days=3)
    d3 = today
    habit.check_ins.create(date=d1)
    habit.check_ins.create(date=d2)
    habit.check_ins.create(date=d3)

    # Filter with both 'from' and 'to'
    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/?from={d2}&to={d3}")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    dates = [item["date"] for item in response.data["results"]]
    assert str(d2) in dates
    assert str(d3) in dates
    assert str(d1) not in dates

    # Filter with only 'from'
    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/?from={d2}")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2

    # Filter with only 'to'
    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/?to={d2}")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_list_checkins_invalid_from_date_returns_400(api_client, habit):
    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/?from=invalid-date")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_list_checkins_invalid_to_date_returns_400(api_client, habit):
    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/?to=invalid-date")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_habit_checkin_serializer_does_not_duplicate_future_date_validation():
    """Future-date validation is handled in service function, not duplicated in serializers."""
    from apps.habits.serializers import CheckInActionSerializer, HabitCheckInSerializer

    future_date = date.today() + timedelta(days=2)
    serializer = HabitCheckInSerializer(data={"date": future_date})
    assert serializer.is_valid()

    action_serializer = CheckInActionSerializer(data={"date": future_date})
    assert action_serializer.is_valid()


@pytest.mark.django_db
def test_list_checkins_nonexistent_habit_404(api_client):
    response = api_client.get("/api/v1/habits/99999/check-ins/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_list_checkins_isolated_to_habit(api_client, habit):
    other_habit = Habit.objects.create(user=habit.user, name="Other Habit")
    today = date.today()
    habit.check_ins.create(date=today)
    other_habit.check_ins.create(date=today)

    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["date"] == str(today)


def test_swagger_docs_accessible(api_client):
    response = api_client.get("/docs/")
    assert response.status_code == status.HTTP_200_OK
    response_no_slash = api_client.get("/docs")
    assert response_no_slash.status_code in [status.HTTP_200_OK, status.HTTP_301_MOVED_PERMANENTLY]
    schema_response = api_client.get("/api/schema/")
    assert schema_response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# MVP Step 3: Streak Calculation in API responses
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_habit_api_exposes_streaks_empty(api_client, habit):
    # Habit with no check-ins
    res = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert "current_streak" in res.data
    assert "longest_streak" in res.data
    assert res.data["current_streak"] == 0
    assert res.data["longest_streak"] == 0

    # Also in list habits
    list_res = api_client.get("/api/v1/habits/")
    assert list_res.status_code == status.HTTP_200_OK
    habit_data = next(h for h in list_res.data["results"] if h["id"] == habit.id)
    assert habit_data["current_streak"] == 0
    assert habit_data["longest_streak"] == 0


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_habit_api_check_and_uncheck_updates_streaks(api_client, habit):
    # 1. Check in yesterday: streak alive ending yesterday
    yesterday = date(2026, 10, 22)
    res1 = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(yesterday)})
    assert res1.status_code == status.HTTP_201_CREATED
    assert res1.data["current_streak"] == 1
    assert res1.data["longest_streak"] == 1

    # Detail API reflects streak=1
    detail_res1 = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert detail_res1.data["current_streak"] == 1
    assert detail_res1.data["longest_streak"] == 1

    # 2. Check in today: consecutive streak reaches 2
    today = date(2026, 10, 23)
    res2 = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(today)})
    assert res2.status_code == status.HTTP_201_CREATED
    assert res2.data["current_streak"] == 2
    assert res2.data["longest_streak"] == 2

    detail_res2 = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert detail_res2.data["current_streak"] == 2
    assert detail_res2.data["longest_streak"] == 2

    # 3. Undo check-in for today: streak reverts to yesterday (1), longest was 2
    uncheck_res = api_client.post(f"/api/v1/habits/{habit.id}/uncheck/", {"date": str(today)})
    assert uncheck_res.status_code == status.HTTP_200_OK
    assert uncheck_res.data["current_streak"] == 1
    assert uncheck_res.data["longest_streak"] == 1

    detail_res3 = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert detail_res3.data["current_streak"] == 1
    assert detail_res3.data["longest_streak"] == 1


@pytest.mark.django_db
@freeze_time("2026-10-23")
def test_habit_api_longest_past_streak_in_response(api_client, habit):
    # Create a 3-day streak in the past: Oct 10, 11, 12
    for offset in [13, 12, 11]:
        d = date(2026, 10, 23) - timedelta(days=offset)
        habit.check_ins.create(date=d)

    # Check in today only (current streak 1, longest streak 3)
    today = date(2026, 10, 23)
    habit.check_ins.create(date=today)

    res = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["current_streak"] == 1
    assert res.data["longest_streak"] == 3


@pytest.mark.django_db
def test_checkin_race_condition_integrity_error_returns_200(api_client, habit, monkeypatch):
    """
    Simulate race condition during concurrent check-in:
    get_or_create encounters IntegrityError due to another thread/process inserting.
    The endpoint must handle IntegrityError and return 200 with the existing check-in instead of 500.
    """
    from django.db import IntegrityError

    from apps.habits.models import HabitCheckIn
    from apps.habits.services import checkin as checkin_service

    today = date.today()
    HabitCheckIn.objects.create(habit=habit, date=today)

    def mock_get_or_create(*args, **kwargs):
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr(checkin_service.HabitCheckIn.objects, "get_or_create", mock_get_or_create)

    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(today)})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "checked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == str(today)
    assert response.data["current_streak"] == 1


# ============================================================================
# Phase 3.4: Frequency API Integration and Filter Verification Tests
# ============================================================================


@pytest.mark.django_db
def test_create_weekday_only_habit_api(api_client):
    payload = {
        "name": "Gym Weekdays",
        "description": "Workout Monday through Friday",
        "color": "#10B981",
        "emoji": "🏋️",
        "frequency_type": "custom",
        "frequency_days": [0, 1, 2, 3, 4],
    }
    response = api_client.post("/api/v1/habits/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Gym Weekdays"
    assert response.data["frequency_type"] == "custom"
    assert response.data["frequency_days"] == [0, 1, 2, 3, 4]
    assert "is_scheduled_today" in response.data


@pytest.mark.django_db
def test_filter_habits_scheduled_today(api_client, user):
    # 1. Daily habit
    Habit.objects.create(
        user=user,
        name="Daily Habit",
        frequency_type="daily",
        frequency_days=[],
    )
    # 2. Weekday habit (Mon-Fri: 0-4)
    Habit.objects.create(
        user=user,
        name="Weekday Habit",
        frequency_type="custom",
        frequency_days=[0, 1, 2, 3, 4],
    )
    # 3. Weekend habit (Sat-Sun: 5, 6)
    Habit.objects.create(
        user=user,
        name="Weekend Habit",
        frequency_type="custom",
        frequency_days=[5, 6],
    )

    # Test on Friday 2026-10-23 (weekday 4):
    # Scheduled today: Daily (1) and Weekday (2) -> count = 2
    # Not scheduled today: Weekend (3) -> count = 1
    with freeze_time("2026-10-23 12:00:00"):
        res_scheduled = api_client.get("/api/v1/habits/?scheduled_today=true")
        assert res_scheduled.status_code == status.HTTP_200_OK
        assert res_scheduled.data["count"] == 2
        names_scheduled = [h["name"] for h in res_scheduled.data["results"]]
        assert "Daily Habit" in names_scheduled
        assert "Weekday Habit" in names_scheduled

        res_unscheduled = api_client.get("/api/v1/habits/?scheduled_today=false")
        assert res_unscheduled.status_code == status.HTTP_200_OK
        assert res_unscheduled.data["count"] == 1
        assert res_unscheduled.data["results"][0]["name"] == "Weekend Habit"

    # Test on Saturday 2026-10-24 (weekday 5):
    # Scheduled today: Daily (1) and Weekend (3) -> count = 2
    # Not scheduled today: Weekday (2) -> count = 1
    with freeze_time("2026-10-24 12:00:00"):
        res_scheduled = api_client.get("/api/v1/habits/?scheduled_today=true")
        assert res_scheduled.status_code == status.HTTP_200_OK
        assert res_scheduled.data["count"] == 2
        names_scheduled = [h["name"] for h in res_scheduled.data["results"]]
        assert "Daily Habit" in names_scheduled
        assert "Weekend Habit" in names_scheduled

        res_unscheduled = api_client.get("/api/v1/habits/?scheduled_today=false")
        assert res_unscheduled.status_code == status.HTTP_200_OK
        assert res_unscheduled.data["count"] == 1
        assert res_unscheduled.data["results"][0]["name"] == "Weekday Habit"


@pytest.mark.django_db
def test_filter_habits_scheduled_today_with_date_override(api_client, user):
    Habit.objects.create(
        user=user,
        name="Daily Habit",
        frequency_type="daily",
    )
    Habit.objects.create(
        user=user,
        name="Weekend Habit",
        frequency_type="custom",
        frequency_days=[5, 6],
    )

    # Current freeze is Friday 2026-10-23, but query overrides date=2026-10-24 (Saturday)
    with freeze_time("2026-10-23 12:00:00"):
        res = api_client.get("/api/v1/habits/?scheduled_today=true&date=2026-10-24")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] == 2


def test_postman_collection_contains_weekday_habit():
    import json
    from pathlib import Path

    collection_path = Path("postman/habit_tracker.postman_collection.json")
    assert collection_path.exists()
    data = json.loads(collection_path.read_text(encoding="utf-8"))

    habits_folder = next(item for item in data["item"] if item["name"] == "2. Habits")
    request_names = [r["name"] for r in habits_folder["item"]]
    assert "Create weekday-only habit" in request_names


@pytest.mark.django_db
def test_filter_habits_scheduled_today_invalid_param_returns_400(api_client, user):
    """Edge Case #5 / Item 2.5: Invalid query param ?scheduled_today=notabool returns 400 Bad Request."""
    res = api_client.get("/api/v1/habits/?scheduled_today=notabool")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "scheduled_today" in res.data


@pytest.mark.django_db
def test_filter_habits_scheduled_today_non_utc_timezone_near_midnight(api_client, user):
    """Edge Case #6: User in non-UTC timezone filtering ?scheduled_today=true near midnight adheres to local day."""
    user.timezone = "Asia/Tokyo"
    user.save()

    # Habit scheduled only on Saturdays (weekday 5)
    Habit.objects.create(
        user=user,
        name="Saturday Habit",
        frequency_type="custom",
        frequency_days=[5],
    )
    # At 2026-10-23 20:00:00 UTC:
    # UTC is Friday 2026-10-23
    # Tokyo is Saturday 2026-10-24 05:00:00
    with freeze_time("2026-10-23 20:00:00"):
        res = api_client.get("/api/v1/habits/?scheduled_today=true")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] == 1
        assert res.data["results"][0]["name"] == "Saturday Habit"


@pytest.mark.django_db
def test_filter_habits_scheduled_today_executes_in_two_queries(
    api_client, user, django_assert_num_queries
):
    """Item 2.1: Filtering by scheduled_today must use ORM filtering in 2 queries, no in-memory table scan."""
    Habit.objects.create(user=user, name="Daily Habit", frequency_type="daily")
    Habit.objects.create(
        user=user, name="Custom Habit", frequency_type="custom", frequency_days=[0, 2, 4]
    )

    with django_assert_num_queries(2):
        res = api_client.get("/api/v1/habits/?scheduled_today=true")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] == 2


@pytest.mark.django_db
def test_list_habits_past_date_avoids_n_plus_one_queries(
    api_client, user, django_assert_num_queries
):
    """Item 2.6: GET /api/v1/habits/?date=YYYY-MM-DD prefetches check-ins and executes in constant 3 queries."""
    today = date(2026, 10, 23)
    past_date = date(2026, 10, 20)

    for i in range(5):
        h = Habit.objects.create(user=user, name=f"Habit {i}")
        h.check_ins.create(date=today)
        h.check_ins.create(date=past_date)

    # 1 count + 1 select habits + 1 prefetch check_ins = 3 queries
    with django_assert_num_queries(3):
        res = api_client.get(f"/api/v1/habits/?date={past_date}")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] == 5
        assert len(res.data["results"]) == 5
