#!/bin/sh
set -e

export PYTHONPATH="$PWD"

if [ -z "${DEV_FILES}" ]; then
    exec uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors
else
    exec uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port $PORT --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi
