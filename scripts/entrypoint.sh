#!/bin/sh
set -e

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting application server..."
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
exec gunicorn --bind "0.0.0.0:${PORT}" --workers "${WEB_CONCURRENCY}" config.wsgi:application
