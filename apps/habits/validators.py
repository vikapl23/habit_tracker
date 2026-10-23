import unicodedata
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

hex_color_validator = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$',
    message='Color must be a valid 3 or 6-digit hex code starting with # (e.g. #3B82F6).'
)


def validate_emoji(value: str) -> None:
    if not value or not value.strip():
        raise ValidationError('Emoji cannot be empty.')
    has_symbol = False
    for char in value:
        cat = unicodedata.category(char)
        if cat.startswith(('L', 'N', 'Z')) or (cat.startswith('P') and ord(char) < 128):
            raise ValidationError('Emoji must be a valid emoji symbol, not text or numbers.')
        if cat in ('So', 'Sk'):
            has_symbol = True
    if not has_symbol:
        raise ValidationError('Emoji must contain a valid emoji symbol.')
