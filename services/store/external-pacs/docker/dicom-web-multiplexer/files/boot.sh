#!/bin/sh

export PYTHONPATH="$PWD" 

# Production
# gunicorn app.main:app --workers $WORKERS --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - 

# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT --workers $WORKERS --forwarded-allow-ips '*'
