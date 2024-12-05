#!/bin/bash

export PYTHONPATH="$PWD" 

if [ "$BACKEND_TYPE" = "backend" ]; then
    WORKING_DIR="$PWD"
    ALEMBIC_DIR="$WORKING_DIR/alembic"
    ENV_FILE="$ALEMBIC_DIR/env.py"
    if [ ! -d "$ALEMBIC_DIR" ] || [ ! -f "$ENV_FILE" ]; then
        echo "Alembic is not initialized. Initializing now..."
        alembic init alembic
        cp env.py "$ENV_FILE"
    else
        echo "Alembic is already initialized."
    fi

    alembic revision --autogenerate -m "Migration"
    alembic upgrade head

    python3 scripts/create_kaapana_instance.py
fi

# # Production
# echo "Running at $APPLICATION_ROOT"
SCRIPT_NAME=/kaapana-$BACKEND_TYPE gunicorn app.$BACKEND_TYPE:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile - 

# Development
# uvicorn app.main:app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT
