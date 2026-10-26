from .base import *

DEBUG = True

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

if not MAILGUN_API_KEY:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

AUTH_THROTTLE_RATE = env("AUTH_THROTTLE_RATE", default="100/minute")
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "auth": AUTH_THROTTLE_RATE,
    },
}
