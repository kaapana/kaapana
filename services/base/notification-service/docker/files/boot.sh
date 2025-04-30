#!/bin/sh

export PYTHONPATH="$PWD"
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2 --root-path $APPLICATION_ROOT --forwarded-allow-ips '*'
