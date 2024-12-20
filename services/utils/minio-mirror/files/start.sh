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
elif [[ $ACTION == "SYNC" ]]; then
    echo "INFO: Start bidirectional sync from local directory ${LOCAL_PATH} into  minio objects at ${MINIO_PATH}"
    RCLONE_SYNC_CMD="rclone bisync --s3-provider "Minio" --s3-endpoint http://$MINIO_SERVICE --s3-access-key-id=$MINIO_USER --s3-secret-access-key=$MINIO_PASSWORD ":s3:/$MINIO_PATH" $LOCAL_PATH --create-empty-src-dirs --compare size,modtime,checksum --slow-hash-sync-only --resilient -MvP --drive-skip-gdocs --fix-case"

    echo "INFO: Inital sync"
    $RCLONE_SYNC_CMD --resync
    while [[ true ]]; do
        sleep ${SYNC_INTERVAL:-20}
        echo "INFO: Sync round"
        set +e
        $RCLONE_SYNC_CMD
        RESULT=$?
        set -e

        case $RESULT in
        0)
            echo "INFO: Sync round successfull"
            continue ;;
        1)
            echo "ERROR: Sync round unsucessfull - recovery possible"
            $RCLONE_SYNC_CMD --resync
            continue ;;
        *)
            echo "ERROR: Sync round unsucessfull - recovery impossible"
            exit 1
        esac
    done
else
    echo "ERROR: ACTION ${ACTION} not supported!!"
    echo "ERROR: ACTION must be one of FETCH or PUSH"
    exit 1
fi