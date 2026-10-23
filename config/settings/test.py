from .local import *

# Speed up tests by using MD5 hasher instead of default Argon2/PBKDF2
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Keep auth throttling disabled in test settings so test runs are not rate-limited
AUTH_THROTTLE_RATE = None
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "auth": None,
    },
}
