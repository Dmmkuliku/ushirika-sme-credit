#!/usr/bin/env bash
set -e
mkdir -p data models

# Ensure admin exists. In production this never resets existing PINs.
python scripts/restore_admin.py || true

# Demo seed data is for local/dev only — never auto-seed production.
if [ "${APP_ENV}" != "production" ] || [ "${ALLOW_DEMO_BOOTSTRAP}" = "true" ]; then
  python scripts/seed_data.py || true
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
