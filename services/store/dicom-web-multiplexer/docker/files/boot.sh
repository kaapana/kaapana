#!/bin/sh

export PYTHONPATH="$PWD" 
APPLICATION_ROOT="/dicom-web-multiplexer"
# forwarded-allow-ips  inc
uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT --workers $WORKERS --root-path $APPLICATION_ROOT --forwarded-allow-ips '*'

# DEVELOP
# SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --access-logfile - --error-logfile -