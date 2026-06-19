#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

export PYTHONPATH="$PWD" 
APPLICATION_ROOT="/dicom-web-filter"

python3 alembic/migrate.py


if [ -z "${DEV_FILES}" ]; then
    # Production
    exec uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors 
else
    # Development
    exec uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi