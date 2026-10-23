from django.contrib import admin
from .models import Habit, HabitCheckIn

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'emoji', 'color', 'is_archived', 'created_at', 'updated_at')
    list_filter = ('is_archived', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)


@admin.register(HabitCheckIn)
class HabitCheckInAdmin(admin.ModelAdmin):
    list_display = ('id', 'habit', 'date', 'created_at')
    list_select_related = ('habit',)
    list_filter = ('date', 'created_at')
    search_fields = ('habit__name',)
    ordering = ('-date',)

