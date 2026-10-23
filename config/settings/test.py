from .local import *

# Speed up tests by using MD5 hasher instead of default Argon2/PBKDF2
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
