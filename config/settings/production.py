import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

# Production security validations
if "SECRET_KEY" not in os.environ or not os.environ["SECRET_KEY"]:
    raise ImproperlyConfigured("SECRET_KEY environment variable must be set in production.")

SECRET_KEY = env("SECRET_KEY")
if SECRET_KEY == "django-insecure-development-secret-key-change-in-production-12345":
    raise ImproperlyConfigured("SECRET_KEY cannot use the insecure default in production.")

if "ALLOWED_HOSTS" not in os.environ or not os.environ["ALLOWED_HOSTS"].strip():
    raise ImproperlyConfigured("ALLOWED_HOSTS environment variable must be set in production.")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be explicitly defined without wildcards in production."
    )


# Production security settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Static files with WhiteNoise
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

AUTH_THROTTLE_RATE = env("AUTH_THROTTLE_RATE", default="5/minute")
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "auth": AUTH_THROTTLE_RATE,
    },
}
