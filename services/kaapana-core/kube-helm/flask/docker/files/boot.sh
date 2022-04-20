#!/bin/sh
# export HELM_PATH='/snap/helm/265/helm'
# export SECRET_KEY='test'
# export APPLICATION_ROOT='/kube-helm' 
echo "Running at $APPLICATION_ROOT"
SCRIPT_NAME=$APPLICATION_ROOT gunicorn -b :5000 --timeout 100 --access-logfile - --error-logfile - run:app