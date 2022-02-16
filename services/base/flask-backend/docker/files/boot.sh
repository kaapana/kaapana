#!/bin/sh
echo "Running at $APPLICATION_ROOT"
SCRIPT_NAME=$APPLICATION_ROOT gunicorn -b :5000 --timeout 100 --access-logfile - --error-logfile - run:app