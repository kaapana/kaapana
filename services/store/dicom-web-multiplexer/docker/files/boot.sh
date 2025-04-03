#!/bin/sh

export PYTHONPATH="$PWD"

uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT --workers $WORKERS --forwarded-allow-ips '*'
