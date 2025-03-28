#!/bin/sh

export PYTHONPATH="$PWD" 
APPLICATION_ROOT="/dicom-web-filter"

if [ -z "${DEV_FILES}" ]; then
    # Production
    echo "Running at $APPLICATION_ROOT"
    SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --workers $WORKERS --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - 
else
    # Development
    uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT --workers $WORKERS --root-path $APPLICATION_ROOT --forwarded-allow-ips '*'
fi