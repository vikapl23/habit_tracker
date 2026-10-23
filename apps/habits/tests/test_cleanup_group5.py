import pytest
from apps.habits.models import Habit, HabitCheckIn
from apps.habits import models, serializers, admin
import config.urls

def test_no_redundant_index_on_habit_checkin():
    redundant_indexes = [
        idx for idx in HabitCheckIn._meta.indexes
        if idx.fields == ['habit', 'date']
    ]
    assert len(redundant_indexes) == 0


def test_no_redundant_docs_url():
    url_patterns = [str(pattern.pattern) for pattern in config.urls.urlpatterns]
    assert 'docs' not in url_patterns


def test_no_class_aliases_clutter():
    assert not hasattr(models, 'CheckIn'), "CheckIn alias should be removed from models"
    assert not hasattr(serializers, 'CheckInSerializer'), "CheckInSerializer alias should be removed"
    assert not hasattr(admin, 'CheckInAdmin'), "CheckInAdmin alias should be removed"


def test_habit_index_sort_direction():
    assert len(Habit._meta.indexes) > 0
    compound_index = Habit._meta.indexes[0]
    assert compound_index.fields == ['is_archived', '-created_at']
