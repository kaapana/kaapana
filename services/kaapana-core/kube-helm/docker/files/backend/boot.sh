#!/bin/bash
# uvicorn app.main:app --reload --host 0.0.0.0 --port 5000

# Production
echo "Running at $APPLICATION_ROOT"
# Workers needs to be one, otherwise the repeated timer object gets confused...
SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --chdir /home/jonas/projects/kaapana/services/kaapana-core/kube-helm/docker/files/backend/app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile - 

# Development
# SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --reload
#uvicorn app.main:app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT