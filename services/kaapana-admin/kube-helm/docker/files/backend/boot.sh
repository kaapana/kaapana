#!/bin/bash

export PYTHONPATH="$PWD" 

if [ -z "${DEV_FILES}" ]; then
    # Production
    gunicorn main:app --chdir /kaapana/app/backend/app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile -
else
    # DEV ENV
    export LOG_LEVEL="debug"

    # DEV cmd
    uvicorn main:app --app-dir /kaapana/app/backend/app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT
fi