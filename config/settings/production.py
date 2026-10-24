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
render_external_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_external_hostname and render_external_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_external_hostname)

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be explicitly defined without wildcards in production."
    )

if "CORS_ALLOWED_ORIGINS" not in os.environ or not os.environ["CORS_ALLOWED_ORIGINS"].strip():
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS environment variable must be set in production."
    )

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
if not CORS_ALLOWED_ORIGINS or "*" in CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must be explicitly defined without wildcards in production."
    )

# Allow relaxing HTTPS-only CORS check (default: True)
CORS_REQUIRE_HTTPS = env.bool("CORS_REQUIRE_HTTPS", default=True)

if CORS_REQUIRE_HTTPS:
    for origin in CORS_ALLOWED_ORIGINS:
        if origin.startswith("http://") or not origin.startswith("https://"):
            raise ImproperlyConfigured(
                f"CORS_ALLOWED_ORIGINS in production must use https:// schemes: {origin}"
            )


# Production security settings (configurable via env, default secure)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)

AUTH_THROTTLE_RATE = env("AUTH_THROTTLE_RATE", default="5/minute")
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "auth": AUTH_THROTTLE_RATE,
    },
}
