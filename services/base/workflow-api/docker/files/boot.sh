#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

export PYTHONPATH="$PWD" 

# Apply all migrations
python3 alembic/migrate.py




if [ -z "${DEV_FILES}" ]; then
    # Production
    uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors --forwarded-allow-ips '*'
else
    # Development
    uvicorn app.main:app --workers 1 --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi
