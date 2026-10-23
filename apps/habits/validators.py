import re
import unicodedata

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

hex_color_validator = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
    message="Color must be a valid 3 or 6-digit hex code starting with # (e.g. #3B82F6).",
)

FLAG = r"[\U0001f1e6-\U0001f1ff]{2}"
KEYCAP = r"[0-9#*]\ufe0f?\u20e3"
TAG_SEQ = r"[\U0001f3f4][\U000e0020-\U000e007e]+[\U000e007f]"
BASE_EMOJI = r"(?:[\u203c-\u32ff\U00010000-\U0010ffff])"
MODIFIER = r"[\U0001f3fb-\U0001f3ff]"
VS = r"[\ufe0e\ufe0f]"

SINGLE_UNIT = rf"(?:{BASE_EMOJI}{VS}?{MODIFIER}?|{KEYCAP}|{TAG_SEQ}|{FLAG})"
ZWJ_SEQUENCE = rf"{SINGLE_UNIT}(?:\u200d{SINGLE_UNIT})*"
SINGLE_EMOJI_PATTERN = rf"^(?:{ZWJ_SEQUENCE}|\U0001f468\U0001f469\U0001f467)$"
SINGLE_EMOJI_REGEX = re.compile(SINGLE_EMOJI_PATTERN)


def validate_emoji(value: str) -> None:
    if not value or not value.strip():
        raise ValidationError("Emoji cannot be empty.")
    if not SINGLE_EMOJI_REGEX.fullmatch(value):
        raise ValidationError("Emoji must be exactly one emoji symbol.")
    for char in value:
        cat = unicodedata.category(char)
        if cat.startswith(("L", "N", "Z")) or (cat.startswith("P") and ord(char) < 128):
            raise ValidationError("Emoji must be a valid emoji symbol, not text or numbers.")
