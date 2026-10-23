import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.habits.models import Habit

User = get_user_model()


@pytest.fixture
def user_a():
    return User.objects.create_user(email="user_a@example.com", password="password123")


@pytest.fixture
def user_b():
    return User.objects.create_user(email="user_b@example.com", password="password123")


@pytest.fixture
def client_a(user_a):
    client = APIClient()
    client.force_authenticate(user=user_a)
    return client


@pytest.fixture
def client_b(user_b):
    client = APIClient()
    client.force_authenticate(user=user_b)
    return client


@pytest.fixture
def unauth_client():
    return APIClient()


@pytest.fixture
def habit_a(user_a):
    return Habit.objects.create(
        user=user_a,
        name="User A Habit",
        description="Habit belonging to User A",
        color="#3B82F6",
        emoji="🎯",
    )


@pytest.mark.django_db
class TestAuthenticationRequired:
    def test_unauthenticated_cannot_list_habits(self, unauth_client):
        res = unauth_client.get("/api/v1/habits/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_create_habit(self, unauth_client):
        res = unauth_client.post("/api/v1/habits/", {"name": "New Habit"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_retrieve_habit(self, unauth_client, habit_a):
        res = unauth_client.get(f"/api/v1/habits/{habit_a.id}/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_update_habit(self, unauth_client, habit_a):
        res = unauth_client.put(f"/api/v1/habits/{habit_a.id}/", {"name": "Updated"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_delete_habit(self, unauth_client, habit_a):
        res = unauth_client.delete(f"/api/v1/habits/{habit_a.id}/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_archive_habit(self, unauth_client, habit_a):
        res = unauth_client.post(f"/api/v1/habits/{habit_a.id}/archive/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_unarchive_habit(self, unauth_client, habit_a):
        res = unauth_client.post(f"/api/v1/habits/{habit_a.id}/unarchive/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_check_habit(self, unauth_client, habit_a):
        res = unauth_client.post(f"/api/v1/habits/{habit_a.id}/check/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_uncheck_habit(self, unauth_client, habit_a):
        res = unauth_client.post(f"/api/v1/habits/{habit_a.id}/uncheck/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_list_checkins(self, unauth_client, habit_a):
        res = unauth_client.get(f"/api/v1/habits/{habit_a.id}/check-ins/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserIsolation:
    def test_user_b_cannot_see_user_a_habits_in_list(self, client_b, habit_a):
        res = client_b.get("/api/v1/habits/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] == 0
        assert len(res.data["results"]) == 0

    def test_user_b_gets_404_on_retrieve_user_a_habit(self, client_b, habit_a):
        res = client_b.get(f"/api/v1/habits/{habit_a.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_user_b_gets_404_on_put_user_a_habit(self, client_b, habit_a):
        res = client_b.put(f"/api/v1/habits/{habit_a.id}/", {"name": "Hacked Habit"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_user_b_gets_404_on_patch_user_a_habit(self, client_b, habit_a):
        res = client_b.patch(f"/api/v1/habits/{habit_a.id}/", {"name": "Hacked Habit"})
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_user_b_gets_404_on_delete_user_a_habit(self, client_b, habit_a):
        res = client_b.delete(f"/api/v1/habits/{habit_a.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert Habit.objects.filter(id=habit_a.id).exists()

    def test_user_b_gets_404_on_archive_user_a_habit(self, client_b, habit_a):
        res = client_b.post(f"/api/v1/habits/{habit_a.id}/archive/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_user_b_gets_404_on_unarchive_user_a_habit(self, client_b, habit_a):
        res = client_b.post(f"/api/v1/habits/{habit_a.id}/unarchive/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_user_b_gets_404_on_check_user_a_habit(self, client_b, habit_a):
        res = client_b.post(f"/api/v1/habits/{habit_a.id}/check/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_user_b_gets_404_on_uncheck_user_a_habit(self, client_b, habit_a):
        res = client_b.post(f"/api/v1/habits/{habit_a.id}/uncheck/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_user_b_gets_404_on_checkins_user_a_habit(self, client_b, habit_a):
        res = client_b.get(f"/api/v1/habits/{habit_a.id}/check-ins/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_habit_creation_assigns_authenticated_user(self, client_a, user_a):
        data = {
            "name": "Meditation",
            "description": "10 mins daily",
            "color": "#10B981",
            "emoji": "🧘",
        }
        res = client_a.post("/api/v1/habits/", data)
        assert res.status_code == status.HTTP_201_CREATED
        created_habit = Habit.objects.get(id=res.data["id"])
        assert created_habit.user == user_a
