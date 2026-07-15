#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

export PYTHONPATH="$PWD" 

if [ -z "${DEV_FILES}" ]; then
    # Production
    exec uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000 --root-path $APPLICATION_ROOT --access-log --use-colors --forwarded-allow-ips '*'
else
    # Development
    exec uvicorn main:app --workers 1 --host 0.0.0.0 --port 8000 --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi
