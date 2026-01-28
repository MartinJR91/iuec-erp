#!/usr/bin/env bash
set -e

python manage.py migrate
python manage.py collectstatic --noinput

# Créer les utilisateurs de démo si ils n'existent pas (idempotent)
python manage.py seed_demo_users 2>/dev/null || echo "Utilisateurs démo déjà créés ou erreur (non bloquant)"

gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
