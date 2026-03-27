#!/bin/bash
set -e

export PYTHONPATH=/app

PG_HOST=${PGHOST:-postgres}
REDIS_HOST=${REDIS_HOST:-redis}
echo "Waiting for PostgreSQL at $PG_HOST..."
PG_USER=${PGUSER:-promptops}
PG_PORT=${PGPORT:-5432}
until pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready."

REDIS_CHECK_URL=${REDIS_URL:-redis://$REDIS_HOST:6379/0}
echo "Waiting for Redis..."
until python -c "import redis; r = redis.Redis.from_url('$REDIS_CHECK_URL'); r.ping()" > /dev/null 2>&1; do
    sleep 1
done
echo "Redis is ready."

echo "Starting Celery worker..."
exec celery -A app.celery_app:celery worker --loglevel=info --concurrency=5
