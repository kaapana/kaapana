#!/bin/sh

RESULT=$(alembic current)

if [ -z "$RESULT" ] || echo "$RESULT" | grep -q "Can't locate revision identified by"; then
    echo "No valid current revision detected. Stamping DB to initial revision..."
    alembic stamp --purge 5d694eb1a7b1 # 0.4.0
fi

# Apply all migrations
alembic upgrade head

export PYTHONPATH="$PWD"
python3 scripts/create_kaapana_instance.py



if [ -z "${DEV_FILES}" ]; then
    # Production
    uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors 
else
    # Development
    uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi