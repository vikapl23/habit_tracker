from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    scope = 'auth'

    def get_rate(self):
        from django.conf import settings
        rate = getattr(settings, 'AUTH_THROTTLE_RATE', None)
        if rate is not None:
            return rate
        throttle_rates = getattr(api_settings, 'DEFAULT_THROTTLE_RATES', {})
        return throttle_rates.get(self.scope)

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
