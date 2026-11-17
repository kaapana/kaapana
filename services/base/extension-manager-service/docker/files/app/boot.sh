#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

export PYTHONPATH="$PWD" 

# Create the tables and the default extension repository once.
# Several workers would otherwise write the same rows at the same time.
python3 startup.py

if [ -z "${DEV_FILES}" ]; then
    # Production
    exec uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000 --root-path $APPLICATION_ROOT --access-log --use-colors --forwarded-allow-ips '*'
else
    # Development
    exec uvicorn main:app --workers 1 --host 0.0.0.0 --port 8000 --root-path $APPLICATION_ROOT --access-log --use-colors --reload --forwarded-allow-ips '*'
fi
