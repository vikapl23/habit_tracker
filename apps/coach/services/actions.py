from __future__ import annotations

import abc
from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from google.genai import types
from rest_framework.exceptions import ValidationError

from apps.habits.models import FrequencyType, Habit, HabitType
from apps.habits.services.streaks import recalculate_habit_streaks

if TYPE_CHECKING:
    from apps.accounts.models import User

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class BaseCoachAction(abc.ABC):
    """Abstract base class for all coach actions in the registry."""

    action_type: str

    @abc.abstractmethod
    def get_function_declaration(self) -> types.FunctionDeclaration:
        """Returns the function declaration schema for Vertex AI Gemini."""

    @abc.abstractmethod
    def validate(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        """Validates payload against business rules and user permissions."""

    @abc.abstractmethod
    def get_summary(self, payload: dict[str, Any]) -> str:
        """Generates a human-readable summary string for the frontend action card."""

    @abc.abstractmethod
    def execute(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        """Executes the action on domain services and models."""


def parse_reminder_time(val: str | None) -> time | None:
    if not val:
        return None
    val = str(val).strip()
    try:
        parts = val.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError()
        if m not in (0, 15, 30, 45):
            raise ValidationError(
                {"reminder_time": "Reminder time minutes must be 0, 15, 30, or 45."}
            )
        return time(h, m)
    except ValidationError:
        raise
    except Exception as err:
        raise ValidationError({"reminder_time": "Invalid time format. Use HH:MM."}) from err


class CreateHabitAction(BaseCoachAction):
    action_type = "create_habit"

    def get_function_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name="create_habit",
            description="Propose creating a new habit for the user. Requires user confirmation before execution.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(
                        type=types.Type.STRING, description="Name or title of the habit"
                    ),
                    "habit_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["boolean", "measurable"],
                        description="Type of habit ('boolean' or 'measurable')",
                    ),
                    "target_value": types.Schema(
                        type=types.Type.NUMBER,
                        description="Target daily quantity if measurable",
                    ),
                    "unit": types.Schema(
                        type=types.Type.STRING,
                        description="Unit of measurement (e.g. glasses, km, minutes, pages)",
                    ),
                    "frequency_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["daily", "custom"],
                        description="Frequency schedule ('daily' or 'custom')",
                    ),
                    "frequency_days": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.INTEGER),
                        description="List of weekday integers 0-6 (0=Mon) if frequency_type is custom",
                    ),
                    "reminder_enabled": types.Schema(
                        type=types.Type.BOOLEAN,
                        description="Whether email reminder is enabled",
                    ),
                    "reminder_time": types.Schema(
                        type=types.Type.STRING,
                        description="Reminder time in HH:MM format (minutes 00, 15, 30, or 45)",
                    ),
                    "color": types.Schema(
                        type=types.Type.STRING,
                        description="Hex color code (e.g. #3B82F6)",
                    ),
                    "emoji": types.Schema(
                        type=types.Type.STRING,
                        description="Single emoji icon (e.g. 🎯)",
                    ),
                },
                required=["name"],
            ),
        )

    def validate(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValidationError({"name": "Name is required."})
        if len(name) > 200:
            raise ValidationError({"name": "Name cannot exceed 200 characters."})

        habit_type = payload.get("habit_type") or HabitType.BOOLEAN
        if habit_type not in (HabitType.BOOLEAN, HabitType.MEASURABLE):
            habit_type = HabitType.BOOLEAN

        target_value = None
        unit = ""
        if habit_type == HabitType.MEASURABLE:
            raw_target = payload.get("target_value")
            if raw_target is None:
                raise ValidationError(
                    {"target_value": "Target value is required for measurable habits."}
                )
            try:
                target_value = round(Decimal(str(raw_target)), 2)
                if target_value <= Decimal("0"):
                    raise ValueError()
                if target_value > Decimal("100000.00"):
                    raise ValueError()
            except Exception as err:
                raise ValidationError(
                    {"target_value": "Target value must be between 0.01 and 100,000."}
                ) from err

            unit = str(payload.get("unit") or "").strip()
            if not unit:
                raise ValidationError({"unit": "Unit is required for measurable habits."})

        frequency_type = payload.get("frequency_type") or FrequencyType.DAILY
        if frequency_type not in (FrequencyType.DAILY, FrequencyType.CUSTOM):
            frequency_type = FrequencyType.DAILY

        frequency_days: list[int] = []
        if frequency_type == FrequencyType.CUSTOM:
            raw_days = payload.get("frequency_days") or []
            if not isinstance(raw_days, list) or not raw_days:
                raise ValidationError(
                    {"frequency_days": "Custom frequency requires at least one weekday."}
                )
            frequency_days = sorted(
                {int(d) for d in raw_days if isinstance(d, int) and 0 <= d <= 6}
            )
            if not frequency_days:
                raise ValidationError(
                    {"frequency_days": "Weekdays must be integers between 0 and 6."}
                )

        reminder_enabled = bool(payload.get("reminder_enabled", False))
        reminder_time_obj = None
        reminder_time_str = None
        if reminder_enabled:
            reminder_time_obj = parse_reminder_time(payload.get("reminder_time"))
            if not reminder_time_obj:
                raise ValidationError(
                    {"reminder_time": "Reminder time is required when reminder is enabled."}
                )
            reminder_time_str = reminder_time_obj.strftime("%H:%M")

        color = str(payload.get("color") or "#3B82F6").strip()
        emoji = str(payload.get("emoji") or "🎯").strip()

        return {
            "name": name,
            "habit_type": habit_type,
            "target_value": float(target_value) if target_value is not None else None,
            "unit": unit,
            "frequency_type": frequency_type,
            "frequency_days": frequency_days,
            "reminder_enabled": reminder_enabled,
            "reminder_time": reminder_time_str,
            "color": color,
            "emoji": emoji,
        }

    def get_summary(self, payload: dict[str, Any]) -> str:
        parts = [f"Create habit: {payload['name']}"]
        if payload.get("habit_type") == HabitType.MEASURABLE:
            parts.append(f"{payload.get('target_value')} {payload.get('unit')}")

        if payload.get("frequency_type") == FrequencyType.DAILY:
            parts.append("daily")
        else:
            days = payload.get("frequency_days") or []
            names = [WEEKDAY_NAMES[d] for d in days if 0 <= d < 7]
            parts.append(f"custom ({', '.join(names)})")

        if payload.get("reminder_enabled") and payload.get("reminder_time"):
            parts.append(f"reminder {payload['reminder_time']}")

        return ", ".join(parts)

    def execute(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        target_val = (
            Decimal(str(payload["target_value"]))
            if payload.get("target_value") is not None
            else None
        )
        r_time = (
            parse_reminder_time(payload.get("reminder_time"))
            if payload.get("reminder_enabled")
            else None
        )

        habit = Habit.objects.create(
            user=user,
            name=payload["name"],
            habit_type=payload["habit_type"],
            target_value=target_val,
            unit=payload.get("unit", ""),
            frequency_type=payload["frequency_type"],
            frequency_days=payload.get("frequency_days", []),
            reminder_enabled=payload.get("reminder_enabled", False),
            reminder_time=r_time,
            color=payload.get("color", "#3B82F6"),
            emoji=payload.get("emoji", "🎯"),
        )
        return {
            "habit_id": habit.id,
            "name": habit.name,
            "detail": "Habit created successfully.",
        }


class UpdateHabitAction(BaseCoachAction):
    action_type = "update_habit"

    def get_function_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name="update_habit",
            description="Propose updating an existing habit (name, target, unit, frequency, or reminder). Requires user confirmation before execution.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "habit_id": types.Schema(
                        type=types.Type.INTEGER, description="ID of the habit to update"
                    ),
                    "name": types.Schema(
                        type=types.Type.STRING, description="New title of the habit"
                    ),
                    "target_value": types.Schema(
                        type=types.Type.NUMBER, description="New target daily value"
                    ),
                    "unit": types.Schema(
                        type=types.Type.STRING, description="New unit of measurement"
                    ),
                    "frequency_type": types.Schema(
                        type=types.Type.STRING,
                        enum=["daily", "custom"],
                        description="New frequency schedule",
                    ),
                    "frequency_days": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.INTEGER),
                        description="New weekday schedule integers",
                    ),
                    "reminder_enabled": types.Schema(
                        type=types.Type.BOOLEAN,
                        description="Whether email reminder is enabled",
                    ),
                    "reminder_time": types.Schema(
                        type=types.Type.STRING,
                        description="Reminder time in HH:MM format",
                    ),
                    "color": types.Schema(type=types.Type.STRING),
                    "emoji": types.Schema(type=types.Type.STRING),
                },
                required=["habit_id"],
            ),
        )

    def validate(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        raw_id = payload.get("habit_id")
        if not raw_id:
            raise ValidationError({"habit_id": "Habit ID is required."})

        try:
            habit = Habit.objects.get(id=int(raw_id), user=user)
        except (Habit.DoesNotExist, ValueError) as err:
            raise ValidationError({"habit_id": "Habit not found or not owned by user."}) from err

        cleaned: dict[str, Any] = {
            "habit_id": habit.id,
            "habit_name": habit.name,
        }

        if "name" in payload and payload["name"] is not None:
            name = str(payload["name"]).strip()
            if not name:
                raise ValidationError({"name": "Name cannot be empty."})
            cleaned["name"] = name

        if "target_value" in payload and payload["target_value"] is not None:
            try:
                tv = round(Decimal(str(payload["target_value"])), 2)
                if tv <= Decimal("0") or tv > Decimal("100000.00"):
                    raise ValueError()
                cleaned["target_value"] = float(tv)
            except Exception as err:
                raise ValidationError(
                    {"target_value": "Target value must be between 0.01 and 100,000."}
                ) from err

        if "unit" in payload and payload["unit"] is not None:
            cleaned["unit"] = str(payload["unit"]).strip()

        if "frequency_type" in payload and payload["frequency_type"] is not None:
            ft = payload["frequency_type"]
            if ft not in (FrequencyType.DAILY, FrequencyType.CUSTOM):
                raise ValidationError({"frequency_type": "Invalid frequency type."})
            cleaned["frequency_type"] = ft

        if "frequency_days" in payload and payload["frequency_days"] is not None:
            raw_days = payload["frequency_days"]
            if not isinstance(raw_days, list):
                raise ValidationError({"frequency_days": "Must be a list of integers."})
            cleaned["frequency_days"] = sorted(
                {int(d) for d in raw_days if isinstance(d, int) and 0 <= d <= 6}
            )

        if "reminder_enabled" in payload:
            cleaned["reminder_enabled"] = bool(payload["reminder_enabled"])

        if "reminder_time" in payload and payload["reminder_time"] is not None:
            r_obj = parse_reminder_time(payload["reminder_time"])
            cleaned["reminder_time"] = r_obj.strftime("%H:%M") if r_obj else None

        if "color" in payload and payload["color"] is not None:
            cleaned["color"] = str(payload["color"]).strip()

        if "emoji" in payload and payload["emoji"] is not None:
            cleaned["emoji"] = str(payload["emoji"]).strip()

        return cleaned

    def get_summary(self, payload: dict[str, Any]) -> str:
        name = payload.get("name") or payload.get("habit_name", "Habit")
        changes = []
        if "target_value" in payload:
            changes.append(f"target {payload['target_value']} {payload.get('unit', '')}".strip())
        if "reminder_time" in payload:
            changes.append(f"reminder {payload['reminder_time']}")
        if "frequency_type" in payload:
            changes.append(f"frequency {payload['frequency_type']}")

        desc = f" ({', '.join(changes)})" if changes else ""
        return f"Update habit: {name}{desc}"

    def execute(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        habit = Habit.objects.get(id=payload["habit_id"], user=user)

        target_changed = False
        if "name" in payload:
            habit.name = payload["name"]
        if "target_value" in payload:
            new_target = Decimal(str(payload["target_value"]))
            if habit.target_value != new_target:
                habit.target_value = new_target
                target_changed = True
        if "unit" in payload:
            habit.unit = payload["unit"]
        if "frequency_type" in payload:
            habit.frequency_type = payload["frequency_type"]
        if "frequency_days" in payload:
            habit.frequency_days = payload["frequency_days"]
        if "reminder_enabled" in payload:
            habit.reminder_enabled = payload["reminder_enabled"]
        if "reminder_time" in payload:
            habit.reminder_time = parse_reminder_time(payload["reminder_time"])
        if "color" in payload:
            habit.color = payload["color"]
        if "emoji" in payload:
            habit.emoji = payload["emoji"]

        habit.save()

        if target_changed:
            recalculate_habit_streaks(habit)

        return {
            "habit_id": habit.id,
            "name": habit.name,
            "detail": "Habit updated successfully.",
        }


class ArchiveHabitAction(BaseCoachAction):
    action_type = "archive_habit"

    def get_function_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name="archive_habit",
            description="Propose soft-archiving an existing habit. Requires user confirmation before execution.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "habit_id": types.Schema(
                        type=types.Type.INTEGER, description="ID of the habit to archive"
                    ),
                },
                required=["habit_id"],
            ),
        )

    def validate(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        raw_id = payload.get("habit_id")
        if not raw_id:
            raise ValidationError({"habit_id": "Habit ID is required."})

        try:
            habit = Habit.objects.get(id=int(raw_id), user=user, is_archived=False)
        except (Habit.DoesNotExist, ValueError) as err:
            raise ValidationError({"habit_id": "Habit not found or already archived."}) from err

        return {
            "habit_id": habit.id,
            "habit_name": habit.name,
        }

    def get_summary(self, payload: dict[str, Any]) -> str:
        name = payload.get("habit_name") or f"ID {payload['habit_id']}"
        return f"Archive habit: {name}"

    def execute(self, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        habit = Habit.objects.get(id=payload["habit_id"], user=user)
        habit.is_archived = True
        habit.save(update_fields=["is_archived", "updated_at"])
        return {
            "habit_id": habit.id,
            "name": habit.name,
            "detail": "Habit archived successfully.",
        }


class ActionRegistry:
    """Registry managing available coach actions and Vertex AI tool definitions."""

    def __init__(self) -> None:
        self._actions: dict[str, BaseCoachAction] = {}

    def register(self, action: BaseCoachAction) -> None:
        self._actions[action.action_type] = action

    def get(self, action_type: str) -> BaseCoachAction | None:
        return self._actions.get(action_type)

    def get_tools(self) -> list[types.Tool]:
        declarations = [action.get_function_declaration() for action in self._actions.values()]
        return [types.Tool(function_declarations=declarations)] if declarations else []


# Default global registry instance with built-in Phase 10 actions
default_action_registry = ActionRegistry()
default_action_registry.register(CreateHabitAction())
default_action_registry.register(UpdateHabitAction())
default_action_registry.register(ArchiveHabitAction())
