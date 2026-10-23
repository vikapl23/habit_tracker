from datetime import date

import freezegun
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.habits.models import Habit, HabitCheckIn

User = get_user_model()


@pytest.fixture
def user_kyiv():
    return User.objects.create_user(
        email="kyiv@example.com", password="Password123!", timezone="Europe/Kyiv"
    )


@pytest.fixture
def user_ny():
    return User.objects.create_user(
        email="ny@example.com", password="Password123!", timezone="America/New_York"
    )


@pytest.fixture
def client_kyiv(user_kyiv):
    client = APIClient()
    client.force_authenticate(user=user_kyiv)
    return client


@pytest.fixture
def client_ny(user_ny):
    client = APIClient()
    client.force_authenticate(user=user_ny)
    return client


@pytest.mark.django_db
class TestTimezoneHandling:
    def test_server_timezone_is_utc(self):
        assert settings.TIME_ZONE == "UTC"

    @freezegun.freeze_time("2026-10-23 23:30:00")
    def test_user_timezone_freezegun_kyiv_vs_new_york(self, user_kyiv, user_ny):
        # At 23:30 UTC:
        # Europe/Kyiv is UTC+3 -> 2026-10-24 02:30:00 (local date 2026-10-24)
        # America/New_York is UTC-4 -> 2026-10-23 19:30:00 (local date 2026-10-23)
        assert user_kyiv.get_today() == date(2026, 10, 24)
        assert user_ny.get_today() == date(2026, 10, 23)

    @freezegun.freeze_time("2026-10-23 23:30:00")
    def test_default_checkin_date_uses_user_timezone(
        self, client_kyiv, client_ny, user_kyiv, user_ny
    ):
        habit_kyiv = Habit.objects.create(user=user_kyiv, name="Kyiv Habit")
        habit_ny = Habit.objects.create(user=user_ny, name="NY Habit")

        res_kyiv = client_kyiv.post(f"/api/v1/habits/{habit_kyiv.id}/check/")
        assert res_kyiv.status_code == status.HTTP_201_CREATED
        assert res_kyiv.data["date"] == "2026-10-24"

        res_ny = client_ny.post(f"/api/v1/habits/{habit_ny.id}/check/")
        assert res_ny.status_code == status.HTTP_201_CREATED
        assert res_ny.data["date"] == "2026-10-23"

    @freezegun.freeze_time("2026-10-23 23:30:00")
    def test_checkin_future_date_validation_per_user_timezone(
        self, client_kyiv, client_ny, user_kyiv, user_ny
    ):
        habit_kyiv = Habit.objects.create(user=user_kyiv, name="Kyiv Habit")
        habit_ny = Habit.objects.create(user=user_ny, name="NY Habit")

        # 2026-10-24 is today for Kyiv, so allowed
        res_kyiv = client_kyiv.post(
            f"/api/v1/habits/{habit_kyiv.id}/check/", {"date": "2026-10-24"}
        )
        assert res_kyiv.status_code == status.HTTP_201_CREATED

        # 2026-10-25 is future for Kyiv, so rejected
        res_kyiv_future = client_kyiv.post(
            f"/api/v1/habits/{habit_kyiv.id}/check/", {"date": "2026-10-25"}
        )
        assert res_kyiv_future.status_code == status.HTTP_400_BAD_REQUEST

        # 2026-10-24 is future for NY (whose today is 2026-10-23), so rejected
        res_ny_future = client_ny.post(
            f"/api/v1/habits/{habit_ny.id}/check/", {"date": "2026-10-24"}
        )
        assert res_ny_future.status_code == status.HTTP_400_BAD_REQUEST

        # 2026-10-23 is today for NY, so allowed
        res_ny = client_ny.post(f"/api/v1/habits/{habit_ny.id}/check/", {"date": "2026-10-23"})
        assert res_ny.status_code == status.HTTP_201_CREATED

    @freezegun.freeze_time("2026-10-23 23:30:00")
    def test_is_checked_today_evaluated_in_user_timezone(
        self, client_kyiv, client_ny, user_kyiv, user_ny
    ):
        habit_kyiv = Habit.objects.create(user=user_kyiv, name="Kyiv Habit")
        habit_ny = Habit.objects.create(user=user_ny, name="NY Habit")

        # Check in on 2026-10-23
        HabitCheckIn.objects.create(habit=habit_kyiv, date=date(2026, 10, 23))
        HabitCheckIn.objects.create(habit=habit_ny, date=date(2026, 10, 23))

        # For Kyiv, today is 2026-10-24, so checked on 2026-10-23 is NOT checked today
        res_kyiv = client_kyiv.get(f"/api/v1/habits/{habit_kyiv.id}/")
        assert res_kyiv.status_code == status.HTTP_200_OK
        assert res_kyiv.data["is_checked_today"] is False

        # For NY, today is 2026-10-23, so checked on 2026-10-23 IS checked today
        res_ny = client_ny.get(f"/api/v1/habits/{habit_ny.id}/")
        assert res_ny.status_code == status.HTTP_200_OK
        assert res_ny.data["is_checked_today"] is True

    @freezegun.freeze_time("2026-10-23 23:30:00")
    def test_streaks_evaluated_in_user_timezone(self, client_kyiv, client_ny, user_kyiv, user_ny):
        habit_kyiv = Habit.objects.create(user=user_kyiv, name="Kyiv Habit")
        habit_ny = Habit.objects.create(user=user_ny, name="NY Habit")

        # Check-in on 2026-10-22
        HabitCheckIn.objects.create(habit=habit_kyiv, date=date(2026, 10, 22))
        HabitCheckIn.objects.create(habit=habit_ny, date=date(2026, 10, 22))

        # For NY (today=2026-10-23), 2026-10-22 was yesterday, so current_streak is still alive (= 1)
        res_ny = client_ny.get(f"/api/v1/habits/{habit_ny.id}/")
        assert res_ny.data["current_streak"] == 1

        # For Kyiv (today=2026-10-24), 2026-10-22 was 2 days ago, so streak is broken (= 0)
        res_kyiv = client_kyiv.get(f"/api/v1/habits/{habit_kyiv.id}/")
        assert res_kyiv.data["current_streak"] == 0

    def test_invalid_date_query_param_returns_400(self, client_kyiv, user_kyiv):
        habit = Habit.objects.create(user=user_kyiv, name="Kyiv Habit")

        # Invalid format on list
        res_list = client_kyiv.get("/api/v1/habits/?date=invalid-date")
        assert res_list.status_code == status.HTTP_400_BAD_REQUEST
        assert "date" in res_list.data

        # Invalid date on detail
        res_detail = client_kyiv.get(f"/api/v1/habits/{habit.id}/?date=2026-13-45")
        assert res_detail.status_code == status.HTTP_400_BAD_REQUEST
        assert "date" in res_detail.data

        # Valid date returns 200
        res_valid = client_kyiv.get("/api/v1/habits/?date=2026-10-23")
        assert res_valid.status_code == status.HTTP_200_OK
