#!/bin/bash
set -e

export PYTHONPATH=/app

PG_HOST=${PGHOST:-postgres}
PG_USER=${PGUSER:-promptops}
PG_PORT=${PGPORT:-5432}
echo "Waiting for PostgreSQL at $PG_HOST..."
until pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready."

echo "Running migrations..."
alembic upgrade head

echo "Running seed script..."
python -m app.seed

echo "Starting API server..."
PORT=${PORT:-8000}
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
