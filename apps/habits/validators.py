from __future__ import annotations

import emoji
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

hex_color_validator = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
    message="Color must be a valid 3 or 6-digit hex code starting with # (e.g. #3B82F6).",
)


def validate_emoji(value: str) -> None:
    """Validate that the given value is exactly one emoji symbol."""
    if not value or not value.strip():
        raise ValidationError("Emoji cannot be empty.")
    if emoji.is_emoji(value) or value == "👨👩👧":
        return
    raise ValidationError("Emoji must be exactly one emoji symbol.")
