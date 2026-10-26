from decimal import Decimal

import pytest
from rest_framework import status

from apps.habits.models import Habit


@pytest.mark.django_db
def test_create_and_retrieve_measurable_habit_api(api_client, user):
    api_client.force_authenticate(user=user)
    payload = {
        "name": "Water",
        "habit_type": "measurable",
        "unit": "glasses",
        "target_value": 8,
    }
    res = api_client.post("/api/v1/habits/", payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["habit_type"] == "measurable"
    assert data["unit"] == "glasses"
    assert data["target_value"] == 8.0
    assert isinstance(data["target_value"], (int, float))
    assert data["today_value"] == 0.0
    assert isinstance(data["today_value"], (int, float))
    assert data["today_progress"] == 0.0
    assert data["is_checked_today"] is False


@pytest.mark.django_db
def test_checkin_measurable_habit_api_numbers(api_client, user):
    api_client.force_authenticate(user=user)
    habit = Habit.objects.create(
        user=user,
        name="Reading",
        habit_type="measurable",
        unit="pages",
        target_value=Decimal("20.00"),
    )
    # Check in: +5 pages
    res = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"value": 5}, format="json")
    assert res.status_code == status.HTTP_200_OK or res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["today_value"] == 5.0
    assert isinstance(data["today_value"], (int, float))
    assert data["today_progress"] == 25.0
    assert data["is_completed"] is False

    # Check in: mode set to 20 -> completed!
    res2 = api_client.post(
        f"/api/v1/habits/{habit.id}/check/", {"value": 20, "mode": "set"}, format="json"
    )
    data2 = res2.json()
    assert data2["today_value"] == 20.0
    assert data2["today_progress"] == 100.0
    assert data2["is_completed"] is True
    assert data2["current_streak"] == 1

    # Uncheck with value 5 -> 15
    res3 = api_client.post(f"/api/v1/habits/{habit.id}/uncheck/", {"value": 5}, format="json")
    data3 = res3.json()
    assert data3["today_value"] == 15.0
    assert data3["status"] == "checked"
    assert data3["is_completed"] is False
    assert data3["current_streak"] == 0


@pytest.mark.django_db
def test_update_target_recalculates_streaks(api_client, user):
    api_client.force_authenticate(user=user)
    habit = Habit.objects.create(
        user=user,
        name="Walking",
        habit_type="measurable",
        unit="km",
        target_value=Decimal("5.00"),
    )
    # Check in 5 km today -> completed (streak = 1)
    api_client.post(f"/api/v1/habits/{habit.id}/check/", {"value": 5, "mode": "set"}, format="json")
    habit.refresh_from_db()
    assert habit.current_streak == 1

    # Update target to 10 km -> day is now incomplete (5 < 10) -> streak must recalculate to 0!
    patch_res = api_client.patch(f"/api/v1/habits/{habit.id}/", {"target_value": 10}, format="json")
    assert patch_res.status_code == status.HTTP_200_OK
    habit.refresh_from_db()
    assert habit.current_streak == 0
    assert patch_res.json()["current_streak"] == 0


@pytest.mark.django_db
def test_habits_list_no_n_plus_one_queries(api_client, user, django_assert_num_queries):
    from decimal import Decimal

    api_client.force_authenticate(user=user)

    # Create 5 habits (mix of boolean and measurable) with checkins
    for i in range(5):
        h = Habit.objects.create(
            user=user,
            name=f"Habit {i}",
            habit_type="measurable" if i % 2 == 0 else "boolean",
            unit="unit" if i % 2 == 0 else "",
            target_value=Decimal("5.00") if i % 2 == 0 else None,
        )
        if i % 2 == 0:
            api_client.post(f"/api/v1/habits/{h.id}/check/", {"value": 5}, format="json")
        else:
            api_client.post(f"/api/v1/habits/{h.id}/check/", {}, format="json")

    # With prefetch_related, fetching 5 habits should take constant queries:
    # Exactly 2 queries: 1 count/paginate + 1 habits (check-ins evaluated from fields without checkin table query)
    with django_assert_num_queries(2):
        res = api_client.get("/api/v1/habits/")
        assert res.status_code == status.HTTP_200_OK
        results = res.json()["results"] if "results" in res.json() else res.json()
        assert len(results) == 5
