#!/bin/bash
# uvicorn app.main:app --reload --host 0.0.0.0 --port 5000

# Production
echo "Running at $APPLICATION_ROOT"
# Workers needs to be one, otherwise the repeated timer object gets confused...
SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile - 

# Development
# # DEV ENV
# export APPLICATION_ROOT="/kube-helm-api"
# export SECRET_KEY="kaapana-secret"
# export REGISTRY_URL=""
# export OFFLINE_MODE="false"
# export LOG_LEVEL="debug"
# export HELM_EXTENSIONS_CACHE="/home/kaapana/extensions"
# export HELM_PATH="/snap/bin/helm"
# export HELM_NAMESPACE="kaapana"
# export KUBECTL_PATH="/snap/bin/microk8s.kubectl"

# # run with custom path
# SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --chdir <path-to-kube-helm-app> --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile - 

# SCRIPT_NAME=$APPLICATION_ROOT gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --reload
#uvicorn app.main:app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT