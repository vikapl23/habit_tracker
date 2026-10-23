from __future__ import annotations

from typing import Any

from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class AuthRateThrottle(SimpleRateThrottle):
    """Rate throttle for authentication endpoints."""

    scope = "auth"

    def get_rate(self) -> str | None:
        """Retrieve throttle rate from settings or default throttle configuration."""
        from django.conf import settings

        rate = getattr(settings, "AUTH_THROTTLE_RATE", None)
        if rate is not None:
            return rate
        throttle_rates = getattr(api_settings, "DEFAULT_THROTTLE_RATES", {})
        return throttle_rates.get(self.scope)

    def get_cache_key(self, request: Request, view: APIView | Any) -> str | None:
        """Generate cache key using client IP identifier and scope."""
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
