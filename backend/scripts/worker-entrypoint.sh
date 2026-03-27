#!/bin/bash
set -e

export PYTHONPATH=/app

PG_HOST=${PGHOST:-postgres}
REDIS_HOST=${REDIS_HOST:-redis}
echo "Waiting for PostgreSQL at $PG_HOST..."
until pg_isready -h "$PG_HOST" -p 5432 -U promptops > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready."

echo "Waiting for Redis at $REDIS_HOST..."
until python -c "import redis; r = redis.Redis(host='$REDIS_HOST', port=6379); r.ping()" > /dev/null 2>&1; do
    sleep 1
done
echo "Redis is ready."

echo "Starting Celery worker..."
exec celery -A app.celery_app:celery worker --loglevel=info --concurrency=5
