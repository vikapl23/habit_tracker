from .base import *

DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

AUTH_THROTTLE_RATE = env('AUTH_THROTTLE_RATE', default='100/minute')
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        **REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}),
        'auth': AUTH_THROTTLE_RATE,
    },
}
