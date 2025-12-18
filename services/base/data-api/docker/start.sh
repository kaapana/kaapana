#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$SCRIPT_DIR"

# Set default values for environment variables
WORKERS=${WORKERS:-4}
PORT=${PORT:-8080}
APPLICATION_ROOT=${APPLICATION_ROOT:-/}

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
if [ -n "${DEV_FILES:-}" ]; then
    exec uvicorn app.main:app --reload --workers $WORKERS --host 0.0.0.0 --port $PORT --access-log --use-colors --root-path $APPLICATION_ROOT
else
    exec uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --access-log --use-colors --root-path $APPLICATION_ROOT
fi
