#!/bin/sh

export PYTHONPATH="$PWD" 
APPLICATION_ROOT="/aii"
# forwarded-allow-ips  inc
uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT --workers $WORKERS --root-path $APPLICATION_ROOT --forwarded-allow-ips '*'
