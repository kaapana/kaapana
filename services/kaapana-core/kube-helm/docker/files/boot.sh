#!/bin/sh
# export HELM_PATH='/snap/helm/265/helm'
# export HELLO_WORLD_USER='jipuser'
# export SECRET_KEY='test'
# export APPLICATION_ROOT='/kube-helm' 
echo "Running at $APPLICATION_ROOT"
SCRIPT_NAME=$APPLICATION_ROOT gunicorn -b :5000 --access-logfile - --error-logfile - run:app