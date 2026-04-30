#!/bin/sh
# Web container entrypoint. Runs once per container start:
#   1. Wait for Postgres to accept connections.
#   2. Apply migrations.
#   3. Seed the knowledge base (idempotent — does nothing if already seeded).
#   4. Create a default superuser if one does not exist.
#   5. Start the Django dev server.
set -e

DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "[web-entrypoint] waiting for database at ${DB_HOST}:${DB_PORT}"
until nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
    sleep 1
done

echo "[web-entrypoint] applying migrations"
python manage.py migrate --noinput

echo "[web-entrypoint] seeding knowledge base (idempotent)"
python seed.py

echo "[web-entrypoint] ensuring default superuser exists"
python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, password=password, email=email)
    print(f"  created superuser '{username}'")
else:
    print(f"  superuser '{username}' already exists")
PY

echo "[web-entrypoint] starting Django dev server on 0.0.0.0:8000"
exec python manage.py runserver 0.0.0.0:8000
