#!/bin/bash
set -e

export PYTHONPATH=/app

PG_HOST=${PGHOST:-postgres}
echo "Waiting for PostgreSQL at $PG_HOST..."
until pg_isready -h "$PG_HOST" -p 5432 -U promptops > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready."

echo "Running migrations..."
alembic upgrade head

echo "Running seed script..."
python -m app.seed

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
