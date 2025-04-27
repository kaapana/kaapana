#!/bin/sh

export PYTHONPATH="$PWD" 
APPLICATION_ROOT="/dicom-web-filter"

# If no Alembic history yet, stamp the initial revision
if [ -z "$(alembic current)" ]; then
  echo "Stamping DB to initial revision..."
  alembic stamp b2c8d2f8b682 # 0.4.0
fi

# Apply all migrations
alembic upgrade head

if [ -z "${DEV_FILES}" ]; then
    # Production
    uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors 
else
    # Development
    uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi