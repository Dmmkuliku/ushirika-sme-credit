#!/usr/bin/env bash
set -e
mkdir -p data models
# Bootstrap admin + demo data if DB is empty / first boot
python scripts/restore_admin.py || true
python scripts/seed_data.py || true
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

# deploy trigger 2026-07-19T15:10:00+03:00 (v1.3.2)
