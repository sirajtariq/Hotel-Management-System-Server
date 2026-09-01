#!/bin/sh
set -e

echo "==> Running Database Migrations..."
uv run python manage.py migrate --noinput

echo "==> Collecting Static Files..."
uv run python manage.py collectstatic --noinput --clear || true

echo "==> Starting Process: $@"
exec "$@"