from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.coach.models import ChatMessage
from apps.habits.models import Habit, HabitCheckIn
from apps.habits.services.statistics import calculate_habit_statistics

if TYPE_CHECKING:
    from apps.accounts.models import User

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def format_frequency(habit: Habit) -> str:
    """Format habit frequency for compact context."""
    if habit.frequency_type == "daily":
        return "daily"
    days = habit.frequency_days or []
    days_names = [WEEKDAY_NAMES[d] for d in sorted(days) if 0 <= d < 7]
    if not days_names:
        return "daily"
    return f"custom ({', '.join(days_names)})"


def format_today_progress(habit: Habit, checkin: HabitCheckIn | None) -> str:
    """Format today's progress string."""
    if habit.habit_type == "boolean":
        if checkin:
            return "completed (1.0/1.0)"
        return "not completed"

    val = float(checkin.value) if checkin else 0.0
    target = float(habit.target_value or 0.0)
    unit = habit.unit or ""
    pct = round((val / target * 100), 1) if target > 0 else 0.0

    if target > 0 and val >= target:
        return f"completed ({val:.1f} / {target:.1f} {unit}, {pct:.0f}%)"
    if val > 0:
        return f"in progress ({val:.1f} / {target:.1f} {unit}, {pct:.0f}%)"
    return f"not started (0.0 / {target:.1f} {unit})"


def build_coach_context(user: User) -> str:
    """
    Build compact context summary for user's active habits:
    - Active habits (name, type, target/unit, frequency, streak, 7/30d %, today's progress, reminder)
    """
    today = user.get_today()
    active_habits = Habit.objects.filter(user=user, is_archived=False).order_by("name")

    if not active_habits.exists():
        return "Active Habits:\nNo active habits found."

    lines = ["Active Habits:"]
    # Prefetch today's check-ins
    today_checkins = {
        c.habit_id: c
        for c in HabitCheckIn.objects.filter(
            habit__in=active_habits,
            date=today,
        )
    }

    for habit in active_habits:
        stats = calculate_habit_statistics(habit, reference_date=today)
        rate_7d = stats.get("completion_rate_7d", 0.0)
        rate_30d = stats.get("completion_rate_30d", 0.0)
        curr_streak = stats.get("current_streak", 0)
        long_streak = stats.get("longest_streak", 0)

        freq_str = format_frequency(habit)
        checkin = today_checkins.get(habit.id)
        today_str = format_today_progress(habit, checkin)

        if habit.habit_type == "measurable" and habit.target_value:
            target_str = f"{float(habit.target_value):.1f} {habit.unit}".strip()
        else:
            target_str = "N/A"

        reminder_str = (
            habit.reminder_time.strftime("%H:%M")
            if habit.reminder_enabled and habit.reminder_time
            else "none"
        )

        habit_line = (
            f"- Habit: {habit.name} | "
            f"Type: {habit.habit_type} | "
            f"Target: {target_str} | "
            f"Frequency: {freq_str} | "
            f"Streak: current {curr_streak}, longest {long_streak} | "
            f"7d Completion: {rate_7d:.0f}% | "
            f"30d Completion: {rate_30d:.0f}% | "
            f"Today: {today_str} | "
            f"Reminder: {reminder_str}"
        )
        lines.append(habit_line)

    return "\n".join(lines)


def format_conversation_history(user: User, limit: int = 10) -> list[dict[str, Any]]:
    """
    Fetch and format the last `limit` messages in chronological order.
    """
    recent_messages = list(ChatMessage.objects.filter(user=user).order_by("-created_at")[:limit])
    recent_messages.reverse()
    return [{"role": msg.role, "content": msg.content} for msg in recent_messages]
