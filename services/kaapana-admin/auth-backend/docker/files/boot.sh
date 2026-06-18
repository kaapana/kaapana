#!/bin/sh

export PYTHONPATH="$PWD" 

if [ -z "${DEV_FILES}" ]; then
    # Production
    exec uvicorn main:app --host 0.0.0.0 --port $PORT
else
    # Development
    exec uvicorn main:app --host 0.0.0.0 --port $PORT --reload --forwarded-allow-ips '*'
fi