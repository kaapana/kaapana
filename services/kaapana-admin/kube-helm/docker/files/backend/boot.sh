#!/bin/bash

export PYTHONPATH="$PWD"

if [ -z "${DEV_FILES}" ]; then
    # Production
    uvicorn app.main:app --workers 1 --host 0.0.0.0 --port 5000 --access-log --use-colors
else
    # Development
    uvicorn app.main:app --workers 1 --host 0.0.0.0 --port 5000 --access-log --use-colors --reload --forwarded-allow-ips '*'
fi