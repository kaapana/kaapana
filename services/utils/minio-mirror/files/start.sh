#!/bin/bash
set -eu

MINIO_BUCKET=$(echo "${MINIO_PATH}/" | cut -d'/' -f1)
mc alias set minio http://${MINIO_SERVICE} ${MINIO_USER} ${MINIO_PASSWORD}
mc mb --ignore-existing minio/${MINIO_BUCKET}
mkdir -p $LOCAL_PATH

exclude=""
if [ -v EXCLUDE ]; then
    IFS=',' read -ra EXCLUSION_PATTERNS <<< "${EXCLUDE}"
    for pattern in "${EXCLUSION_PATTERNS[@]}"; do
        exclude="${exclude} --exclude ${pattern}"
    done
fi

mc cp /kaapana/app/README.txt minio/$MINIO_BUCKET/README.txt

if [[ $ACTION == "FETCH" ]]; then
    echo "INFO: Start to mirror minio objects from ${MINIO_PATH} into local directory ${LOCAL_PATH}"
    mc cp /kaapana/app/input_from_minio.txt minio/$MINIO_PATH/input_from_minio.txt
    mc mirror --watch ${exclude} minio/$MINIO_PATH $LOCAL_PATH 
elif [[ $ACTION == "PUSH" ]]; then
    echo "INFO: Start to mirror data from local directory ${LOCAL_PATH} into  minio objects at ${MINIO_PATH}"
    cp /kaapana/app/output_from_application.txt $LOCAL_PATH/output_from_application.txt
    mc mirror --watch ${exclude} $LOCAL_PATH minio/$MINIO_PATH 
else
    echo "ERROR: ACTION ${ACTION} not supported!!"
    echo "ERROR: ACTION must be one of FETCH or PUSH"
    exit 1
fi