#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting container initialization..."

# Load environment if present
if [ -f .env ]; then
  echo "[entrypoint] Loading .env"
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# Wait for PostgreSQL if configured
if [ "${DB_ENGINE:-django.db.backends.postgresql}" = "django.db.backends.postgresql" ]; then
  DB_HOST=${DB_HOST:-db}
  DB_PORT=${DB_PORT:-5432}
  DB_USER=${DB_USER:-postgres}
  echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
  until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" >/dev/null 2>&1; do
    sleep 1
  done
  echo "[entrypoint] PostgreSQL is ready."
fi

echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

if [ "${DISABLE_COLLECTSTATIC:-0}" != "1" ]; then
  echo "[entrypoint] Collecting static files..."
  python manage.py collectstatic --noinput || echo "[entrypoint] collectstatic failed or skipped"
else
  echo "[entrypoint] Skipping collectstatic (DISABLE_COLLECTSTATIC=1)."
fi

# Debug: show effective ALLOWED_HOSTS & DEBUG in container
echo "[entrypoint] Env ALLOWED_HOSTS: ${ALLOWED_HOSTS:-<unset>}"
python manage.py shell -c "from django.conf import settings; print('[entrypoint] Settings ALLOWED_HOSTS:', settings.ALLOWED_HOSTS); print('[entrypoint] Settings DEBUG:', settings.DEBUG)"

# Optionally create a superuser non-interactively when env vars are provided
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo "[entrypoint] Ensuring superuser ${DJANGO_SUPERUSER_USERNAME} exists..."
  python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.getenv("DJANGO_SUPERUSER_USERNAME")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
if username and password:
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"[entrypoint] Superuser '{username}' created.")
    else:
        print(f"[entrypoint] Superuser '{username}' already exists.")
PY
fi

echo "[entrypoint] Initialization complete. Starting app..."
exec "$@"
