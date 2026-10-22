import pytest
from datetime import date, timedelta
from rest_framework import status
from apps.habits.models import Habit, HabitCheckIn

@pytest.mark.django_db
def test_list_habits(api_client, habit):
    archived_habit = Habit.objects.create(name="Archived Habit", is_archived=True)
    
    # By default, archived habits should not be listed
    response = api_client.get("/api/v1/habits/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == habit.id
    assert "current_streak" in response.data[0]
    assert "longest_streak" in response.data[0]
    assert "is_checked_today" in response.data[0]

    # With include_archived=true
    response = api_client.get("/api/v1/habits/?include_archived=true")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


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
    assert response.data["is_checked_today"] is False


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
def test_check_in_today(api_client, habit):
    today = date.today()
    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "checked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == str(today)
    assert response.data["current_streak"] == 1
    assert response.data["longest_streak"] == 1
    assert HabitCheckIn.objects.filter(habit=habit, date=today).exists()


@pytest.mark.django_db
def test_check_in_idempotency(api_client, habit):
    today = date.today()
    # First check
    res1 = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(today)})
    assert res1.status_code == status.HTTP_201_CREATED
    # Second check (idempotent)
    res2 = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(today)})
    assert res2.status_code == status.HTTP_200_OK
    assert res2.data["status"] == "checked"
    assert HabitCheckIn.objects.filter(habit=habit, date=today).count() == 1


@pytest.mark.django_db
def test_cannot_check_in_future_date(api_client, habit):
    future_date = date.today() + timedelta(days=1)
    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(future_date)})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "date" in response.data


@pytest.mark.django_db
def test_uncheck_existing_checkin(api_client, habit):
    today = date.today()
    HabitCheckIn.objects.create(habit=habit, date=today)
    response = api_client.post(f"/api/v1/habits/{habit.id}/uncheck/", {"date": str(today)})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "unchecked"
    assert response.data["habit_id"] == habit.id
    assert response.data["date"] == str(today)
    assert not HabitCheckIn.objects.filter(habit=habit, date=today).exists()


@pytest.mark.django_db
def test_uncheck_nonexistent_checkin(api_client, habit):
    today = date.today()
    response = api_client.post(f"/api/v1/habits/{habit.id}/uncheck/", {"date": str(today)})
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_get_habit_checkins_history(api_client, habit):
    today = date.today()
    yesterday = today - timedelta(days=1)
    HabitCheckIn.objects.create(habit=habit, date=yesterday)
    HabitCheckIn.objects.create(habit=habit, date=today)
    
    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2

    # Filter with ?from=&to=
    response = api_client.get(f"/api/v1/habits/{habit.id}/check-ins/?from={today}&to={today}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["date"] == str(today)


def test_swagger_docs_accessible(api_client):
    response = api_client.get("/docs/")
    assert response.status_code == status.HTTP_200_OK
    response_no_slash = api_client.get("/docs")
    assert response_no_slash.status_code in [status.HTTP_200_OK, status.HTTP_301_MOVED_PERMANENTLY]
    schema_response = api_client.get("/api/schema/")
    assert schema_response.status_code == status.HTTP_200_OK

