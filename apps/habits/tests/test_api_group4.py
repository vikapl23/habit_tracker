import pytest
from datetime import date, timedelta
from freezegun import freeze_time
from rest_framework import status
from apps.habits.models import Habit

@pytest.mark.django_db
def test_habit_serializer_includes_is_checked_today(api_client, habit):
    # Not checked today
    res = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert "is_checked_today" in res.data
    assert res.data["is_checked_today"] is False

    # Check in today
    api_client.post(f"/api/v1/habits/{habit.id}/check/")
    res = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert res.data["is_checked_today"] is True


@pytest.mark.django_db
def test_habit_serializer_is_checked_today_with_date_query_param(api_client, habit):
    past_date = date.today() - timedelta(days=2)
    habit.check_ins.create(date=past_date)

    # Without query param, today is not checked
    res = api_client.get(f"/api/v1/habits/{habit.id}/")
    assert res.data["is_checked_today"] is False

    # With ?date=past_date, it should report True
    res = api_client.get(f"/api/v1/habits/{habit.id}/?date={past_date}")
    assert res.data["is_checked_today"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("invalid_color", ["blue", "123456", "#12", "#1234567", "#zzzzzz", "red"])
def test_create_habit_invalid_color_rejected(api_client, invalid_color):
    payload = {"name": "Test Habit", "color": invalid_color}
    res = api_client.post("/api/v1/habits/", payload, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "color" in res.data


@pytest.mark.django_db
@pytest.mark.parametrize("valid_color", ["#3B82F6", "#fff", "#FFFFFF", "#10B981"])
def test_create_habit_valid_color_accepted(api_client, valid_color):
    payload = {"name": "Test Habit", "color": valid_color}
    res = api_client.post("/api/v1/habits/", payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["color"] == valid_color


@pytest.mark.django_db
@freeze_time("2026-10-23")
@pytest.mark.parametrize("invalid_emoji", ["", "   ", "not-an-emoji", "123", "hello 🎯", "💧💧"])
def test_create_habit_invalid_emoji_rejected(api_client, invalid_emoji):
    payload = {"name": "Test Habit", "emoji": invalid_emoji}
    res = api_client.post("/api/v1/habits/", payload, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "emoji" in res.data


@pytest.mark.django_db
@freeze_time("2026-10-23")
@pytest.mark.parametrize("valid_emoji", ["👍🏽", "🇺🇦", "❤️", "👨👩👧", "👨‍👩‍👧", "💧", "🎯"])
def test_create_habit_valid_emoji_accepted(api_client, valid_emoji):
    payload = {"name": "Test Habit", "emoji": valid_emoji}
    res = api_client.post("/api/v1/habits/", payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["emoji"] == valid_emoji


@pytest.mark.django_db
def test_pagination_on_habits_and_checkins_list(api_client, habit):
    # Habit list pagination
    res = api_client.get("/api/v1/habits/")
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.data, dict)
    assert "count" in res.data
    assert "next" in res.data
    assert "previous" in res.data
    assert "results" in res.data

    # Check-ins list pagination
    habit.check_ins.create(date=date.today())
    res = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/")
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.data, dict)
    assert "count" in res.data
    assert "results" in res.data


@pytest.mark.django_db
def test_safer_archived_filtering_on_detail_views(api_client):
    archived_habit = Habit.objects.create(name="Archived Habit", is_archived=True)

    # Retrieval of archived habit should succeed
    res = api_client.get(f"/api/v1/habits/{archived_habit.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["id"] == archived_habit.id
    assert res.data["is_archived"] is True

    # Check action on archived habit should succeed
    res = api_client.post(f"/api/v1/habits/{archived_habit.id}/check/")
    assert res.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


def test_custom_actions_openapi_schema(api_client):
    res = api_client.get("/api/schema/")
    assert res.status_code == status.HTTP_200_OK
    paths = res.data["paths"]

    archive_op = paths["/api/v1/habits/{id}/archive/"]["post"]
    assert "requestBody" not in archive_op

    unarchive_op = paths["/api/v1/habits/{id}/unarchive/"]["post"]
    assert "requestBody" not in unarchive_op

    check_op = paths["/api/v1/habits/{id}/check/"]["post"]
    assert "requestBody" in check_op
    check_req_ref = check_op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert "CheckInAction" in check_req_ref

