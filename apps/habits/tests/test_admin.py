from apps.habits.admin import HabitCheckInAdmin

def test_habit_checkin_admin_list_select_related():
    assert HabitCheckInAdmin.list_select_related == ('habit',)
