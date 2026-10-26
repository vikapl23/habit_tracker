import importlib
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.habits.models import Habit, HabitCheckIn


@pytest.mark.django_db
def test_create_habit(user):
    habit = Habit.objects.create(
        user=user, name="Morning Jog", description="Jog for 30 minutes", color="#10B981", emoji="🏃"
    )
    assert habit.id is not None
    assert habit.name == "Morning Jog"
    assert habit.description == "Jog for 30 minutes"
    assert habit.color == "#10B981"
    assert habit.emoji == "🏃"
    assert habit.is_archived is False
    assert habit.created_at is not None
    assert habit.updated_at is not None
    assert str(habit) == "Morning Jog"


@pytest.mark.django_db
def test_create_checkin(habit):
    checkin_date = habit.user.get_today()
    checkin = HabitCheckIn.objects.create(habit=habit, date=checkin_date)
    assert checkin.id is not None
    assert checkin.habit == habit
    assert checkin.date == checkin_date
    assert checkin.created_at is not None
    assert f"{habit.name} - {checkin_date}" in str(checkin)


@pytest.mark.django_db
def test_unique_checkin_per_date_constraint(habit):
    checkin_date = habit.user.get_today()
    HabitCheckIn.objects.create(habit=habit, date=checkin_date)
    with pytest.raises(IntegrityError):
        HabitCheckIn.objects.create(habit=habit, date=checkin_date)


@pytest.mark.django_db
def test_checkin_model_save_does_not_call_clean(habit, monkeypatch):
    """Model save() must not call clean(), avoiding overhead on fixtures/bulk ops."""
    clean_called = False

    def mock_clean():
        nonlocal clean_called
        clean_called = True

    checkin = HabitCheckIn(habit=habit, date=habit.user.get_today())
    monkeypatch.setattr(checkin, "clean", mock_clean)
    checkin.save()
    assert not clean_called, "HabitCheckIn.save() should not call clean()"


@pytest.mark.django_db
def test_checkin_model_allows_future_date_for_fixtures_and_bulk(habit):
    """Model clean() and save() do not reject future dates, leaving that to the service."""
    future_date = habit.user.get_today() + timedelta(days=1)
    checkin = HabitCheckIn.objects.create(habit=habit, date=future_date)
    assert checkin.id is not None
    checkin.full_clean()  # Should not raise


@pytest.mark.django_db
def test_cascade_delete_habit_deletes_checkins(habit):
    HabitCheckIn.objects.create(habit=habit, date=habit.user.get_today())
    assert HabitCheckIn.objects.filter(habit=habit).count() == 1
    habit.delete()
    assert HabitCheckIn.objects.filter(habit_id=habit.id).count() == 0


@pytest.mark.django_db
def test_habit_requires_user():
    with pytest.raises(IntegrityError):
        Habit.objects.create(name="No User Habit", color="#3B82F6", emoji="🎯")


@pytest.mark.django_db
def test_habit_belongs_to_user(user):
    habit = Habit.objects.create(user=user, name="User Habit", color="#3B82F6", emoji="🎯")
    assert habit.user == user
    assert habit in user.habits.all()


@pytest.mark.django_db
def test_delete_user_cascades_to_habits(user):
    Habit.objects.create(user=user, name="Habit 1")
    Habit.objects.create(user=user, name="Habit 2")
    assert user.habits.count() == 2
    user_id = user.id
    user.delete()
    assert Habit.objects.filter(user_id=user_id).count() == 0


@pytest.mark.django_db
def test_measurable_habit_fields_and_validation(user):
    from decimal import Decimal

    # Valid measurable habit
    habit = Habit(
        user=user,
        name="Drink Water",
        habit_type="measurable",
        unit="glasses",
        target_value=Decimal("8.00"),
    )
    habit.full_clean()
    habit.save()
    assert habit.habit_type == "measurable"
    assert habit.unit == "glasses"
    assert habit.target_value == Decimal("8.00")

    # Measurable habit requires unit
    invalid_no_unit = Habit(
        user=user,
        name="Invalid",
        habit_type="measurable",
        unit="",
        target_value=Decimal("5.00"),
    )
    with pytest.raises(ValidationError) as exc:
        invalid_no_unit.full_clean()
    assert "unit" in exc.value.message_dict

    # Measurable habit requires target_value > 0
    invalid_zero_target = Habit(
        user=user,
        name="Invalid",
        habit_type="measurable",
        unit="km",
        target_value=Decimal("0.00"),
    )
    with pytest.raises(ValidationError) as exc:
        invalid_zero_target.full_clean()
    assert "target_value" in exc.value.message_dict

    # Measurable habit target_value max 100,000
    invalid_max_target = Habit(
        user=user,
        name="Invalid",
        habit_type="measurable",
        unit="km",
        target_value=Decimal("100000.01"),
    )
    with pytest.raises(ValidationError) as exc:
        invalid_max_target.full_clean()
    assert "target_value" in exc.value.message_dict

    # Boolean habit clears unit and target_value or errors if provided
    bool_habit = Habit(
        user=user,
        name="Read book",
        habit_type="boolean",
        unit="pages",
        target_value=Decimal("10.00"),
    )
    with pytest.raises(ValidationError) as exc:
        bool_habit.full_clean()
    assert "unit" in exc.value.message_dict or "target_value" in exc.value.message_dict


@pytest.mark.django_db
def test_habit_checkin_value_field(habit):
    from decimal import Decimal

    checkin = HabitCheckIn.objects.create(
        habit=habit,
        date=habit.user.get_today(),
        value=Decimal("2.50"),
    )
    assert checkin.value == Decimal("2.50")


def test_admin_registration():
    assert Habit in admin.site._registry
    assert HabitCheckIn in admin.site._registry


def test_habit_model_validation_rejects_invalid_color():
    habit = Habit(name="Test", color="invalid-hex")
    with pytest.raises(ValidationError):
        habit.full_clean()


def test_habit_model_validation_rejects_invalid_emoji():
    habit = Habit(name="Test", emoji="💧💧")
    with pytest.raises(ValidationError):
        habit.full_clean()


@pytest.mark.django_db
def test_habit_model_validation_accepts_valid_complex_emojis(user):
    for emoji in ["👍🏽", "🇺🇦", "❤️", "👨👩👧", "👨‍👩‍👧"]:
        habit = Habit(user=user, name="Test", emoji=emoji)
        habit.full_clean()  # Should not raise


@pytest.mark.django_db
def test_habit_default_frequency(user):
    habit = Habit.objects.create(user=user, name="Daily Habit")
    assert habit.frequency_type == "daily"
    assert habit.frequency_days == []
    assert habit.is_scheduled_on(date(2026, 10, 23))  # Friday
    assert habit.is_scheduled_on(date(2026, 10, 24))  # Saturday
    assert habit.is_scheduled_today() is True


@pytest.mark.django_db
def test_habit_custom_frequency_scheduling(user):
    # Mon (0), Wed (2), Fri (4)
    habit = Habit.objects.create(
        user=user,
        name="Gym",
        frequency_type="custom",
        frequency_days=[0, 2, 4],
    )
    assert habit.frequency_type == "custom"
    assert habit.frequency_days == [0, 2, 4]
    assert habit.is_scheduled_on(date(2026, 10, 23)) is True  # Friday is 4
    assert habit.is_scheduled_on(date(2026, 10, 24)) is False  # Saturday is 5
    assert habit.is_scheduled_on(date(2026, 10, 25)) is False  # Sunday is 6
    assert habit.is_scheduled_on(date(2026, 10, 26)) is True  # Monday is 0


@pytest.mark.django_db
def test_habit_validation_rejects_empty_frequency_days_for_custom(user):
    habit = Habit(user=user, name="Gym", frequency_type="custom", frequency_days=[])
    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()
    assert "frequency_days" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_days",
    [
        [-1],
        [7],
        [0, 7],
        ["mon"],
        [0, 1, 1],  # Duplicate
        [2, 3, 2],  # Duplicate
    ],
)
def test_habit_validation_rejects_invalid_frequency_days(user, invalid_days):
    habit = Habit(user=user, name="Gym", frequency_type="custom", frequency_days=invalid_days)
    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()
    assert "frequency_days" in exc_info.value.message_dict


@pytest.mark.django_db
def test_habit_validation_rejects_invalid_frequency_type(user):
    habit = Habit(user=user, name="Gym", frequency_type="yearly", frequency_days=[0])
    with pytest.raises(ValidationError) as exc_info:
        habit.full_clean()
    assert "frequency_type" in exc_info.value.message_dict


@pytest.mark.django_db
def test_habit_recalculates_streaks_on_frequency_change(user, monkeypatch):
    from apps.habits.services.habits import update_habit

    habit = Habit.objects.create(user=user, name="Gym")
    recalculate_called = False

    def mock_recalculate(h, reference_date=None):
        nonlocal recalculate_called
        recalculate_called = True
        return h

    monkeypatch.setattr("apps.habits.services.habits.recalculate_habit_streaks", mock_recalculate)
    update_habit(habit, frequency_type="custom", frequency_days=[0, 2, 4])
    assert recalculate_called is True


def test_habit_is_scheduled_on_none_frequency_days_safe():
    """Edge Case #8 / Item 2.3: Habit.is_scheduled_on should not raise TypeError when frequency_days is None."""
    habit = Habit(name="Gym", frequency_type="custom", frequency_days=None)
    assert habit.is_scheduled_on(date(2026, 10, 23)) is False


@pytest.mark.django_db
def test_habit_save_invokes_clean_on_invalid_data(user):
    """Item 2.4: Habit.save() executes clean(), rejecting invalid frequency data."""
    with pytest.raises(ValidationError) as exc_info:
        Habit.objects.create(
            user=user, name="Bad Custom Habit", frequency_type="custom", frequency_days=[]
        )
    assert "frequency_days" in exc_info.value.message_dict


@pytest.mark.django_db
def test_habit_save_does_not_dispatch_extra_select_query(user, django_assert_num_queries):
    """Item 2.2: Habit.save() uses in-memory loaded values, avoiding extra SELECT queries."""
    habit = Habit.objects.create(user=user, name="Reading", frequency_type="daily")
    # Reload habit from DB to simulate standard workflow
    loaded = Habit.objects.get(id=habit.id)
    loaded.name = "Reading Books"

    with django_assert_num_queries(1):
        loaded.save()


@pytest.mark.django_db
def test_data_migration_populates_existing_habits(user):
    """Items 1.2 & 2.7: set_existing_habits_daily updates all existing habits to daily with frequency_days=[]."""
    migration_0004 = importlib.import_module("apps.habits.migrations.0004_populate_daily_frequency")
    set_existing_habits_daily = migration_0004.set_existing_habits_daily

    habit = Habit.objects.create(user=user, name="Old Habit")
    Habit.objects.filter(id=habit.id).update(frequency_type="", frequency_days=[99])

    set_existing_habits_daily(apps, None)

    habit.refresh_from_db()
    assert habit.frequency_type == "daily"
    assert habit.frequency_days == []


@pytest.mark.django_db
def test_data_migration_backfills_last_check_in_value(user):
    """Item 3: Migration backfills last_check_in_value = 1.00 for habits with last_check_in_date."""
    migration_0007 = importlib.import_module(
        "apps.habits.migrations.0007_backfill_last_check_in_value"
    )
    backfill_func = migration_0007.backfill_last_check_in_value

    habit_checked = Habit.objects.create(
        user=user, name="Checked Habit", last_check_in_date=user.get_today()
    )
    Habit.objects.filter(id=habit_checked.id).update(last_check_in_value=Decimal("0.00"))

    habit_unchecked = Habit.objects.create(
        user=user, name="Unchecked Habit", last_check_in_date=None
    )
    Habit.objects.filter(id=habit_unchecked.id).update(last_check_in_value=Decimal("0.00"))

    backfill_func(apps, None)

    habit_checked.refresh_from_db()
    assert habit_checked.last_check_in_value == Decimal("1.00")

    habit_unchecked.refresh_from_db()
    assert habit_unchecked.last_check_in_value == Decimal("0.00")
