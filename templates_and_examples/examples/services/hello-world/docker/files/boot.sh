#!/bin/sh

SCRIPT_NAME=$APPLICATION_ROOT gunicorn -b :5000 --access-logfile - --error-logfile - run:app