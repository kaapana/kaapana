#!/bin/bash
set -eu

MINIO_BUCKET=$(echo "${MINIO_PATH}/" | cut -d'/' -f1)
mc alias set minio http://${MINIO_SERVICE} ${MINIO_USER} ${MINIO_PASSWORD}
mc mb --ignore-existing minio/${MINIO_BUCKET}
mkdir -p $LOCAL_PATH

if [[ $ACTION == "FETCH" ]]; then
    echo "INFO: Start to mirror minio objects from ${MINIO_PATH} into local directory ${LOCAL_PATH}"
    mc mirror minio/$MINIO_PATH $LOCAL_PATH --watch
elif [[ $ACTION == "PUSH" ]]; then
    echo "INFO: Start to mirror data from local directory ${LOCAL_PATH} into  minio objects at ${MINIO_PATH}"
    mc mirror $LOCAL_PATH minio/$MINIO_PATH --watch
else
    echo "ERROR: ACTION ${ACTION} not supported!!"
    echo "ERROR: ACTION must be one of FETCH or PUSH"
    exit 1
fi