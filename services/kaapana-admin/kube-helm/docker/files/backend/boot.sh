#!/bin/bash

if [ -z "${DEV_FILES}" ]; then
    # Production
    gunicorn main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --access-logfile - --error-logfile -
else
    # DEV ENV
    export APPLICATION_ROOT="/kube-helm-api"
    export SECRET_KEY="kaapana-secret"
    export REGISTRY_URL=""
    export OFFLINE_MODE="false"
    export LOG_LEVEL="debug"
    export HELM_EXTENSIONS_CACHE="/home/kaapana/extensions"
    export HELM_PLATFORMS_CACHE="/home/kaapana/platforms"
    export HELM_PATH="/snap/bin/helm"
    export HELM_NAMESPACE="admin"
    export KUBECTL_PATH="/snap/bin/microk8s.kubectl"

    # DEV cmd
    uvicorn main:app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT
fi