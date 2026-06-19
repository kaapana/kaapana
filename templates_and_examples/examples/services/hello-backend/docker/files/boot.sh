#!/bin/sh

flask db init
flask db migrate
flask db upgrade

SCRIPT_NAME=$APPLICATION_ROOT exec gunicorn -b :5000 --access-logfile - --error-logfile - run:app