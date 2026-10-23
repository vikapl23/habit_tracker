import pytest
from datetime import date, timedelta
from freezegun import freeze_time
from rest_framework import status
from apps.habits.models import Habit

@pytest.mark.django_db
def test_list_habits(api_client, habit):
    archived_habit = Habit.objects.create(user=habit.user, name="Archived Habit", is_archived=True)
    
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

    # 1 query for count + 1 query to fetch habits + 1 query to prefetch check_ins = 3 queries
    with django_assert_num_queries(3):
        response = api_client.get("/api/v1/habits/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 5
        assert len(response.data["results"]) == 5


@pytest.mark.django_db
def test_create_habit(api_client):
    payload = {
        "name": "Morning Meditation",
        "description": "10 minutes of mindfulness",
        "color": "#10B981",
        "emoji": "🧘"
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
        "emoji": "🚰"
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


def test_habit_checkin_serializer_rejects_future_date():
    from apps.habits.serializers import HabitCheckInSerializer
    future_date = date.today() + timedelta(days=2)
    serializer = HabitCheckInSerializer(data={'date': future_date})
    assert not serializer.is_valid()
    assert 'date' in serializer.errors


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
from freezegun import freeze_time

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

