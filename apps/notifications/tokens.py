from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core import signing

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

UNSUBSCRIBE_SALT = "habit-tracker-notifications-unsubscribe"


def generate_unsubscribe_token(user: AbstractBaseUser) -> str:
    """Generate a signed cryptographic token for unauthenticated unsubscribe."""
    return signing.dumps({"user_id": user.pk}, salt=UNSUBSCRIBE_SALT)


def verify_unsubscribe_token(token: str) -> int | None:
    """Verify and decode the signed unsubscribe token, returning the user_id or None."""
    try:
        data = signing.loads(token, salt=UNSUBSCRIBE_SALT)
        if isinstance(data, dict) and "user_id" in data:
            return data["user_id"]
        return None
    except (signing.BadSignature, ValueError, TypeError):
        return None


def build_unsubscribe_url(user: AbstractBaseUser, base_url: str | None = None) -> str:
    """Build a complete unsubscribe URL for a given user."""
    token = generate_unsubscribe_token(user)
    if not base_url:
        base_url = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    else:
        base_url = base_url.rstrip("/")
    return f"{base_url}/api/v1/notifications/unsubscribe/{token}/"
