#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

python3 alembic/migrate.py

export PYTHONPATH="$PWD"
python3 scripts/create_kaapana_instance.py

if [ -z "${DEV_FILES}" ]; then
    # Production
    exec uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors 
else
    # Development
    exec uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi