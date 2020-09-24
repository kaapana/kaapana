#!/bin/sh

mc config host add jip http://minio-service.store.svc:9000/ $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc admin user add jip landing landingminio
mc mb jip/uploads
EVENT_LIST=$(mc event list jip/uploads | grep arn:minio:sqs::dicomsupload:webhook)
if [ "${EVENT_LIST%webhook*}" = "arn:minio:sqs::dicomsupload:" ]; then
    echo 'Event already set!'
    exit 0
fi

mc admin policy add jip putupload permissions_uploads.json
mc admin policy set jip putupload user=landing
mc admin config set jip notify_webhook:dicomsupload queue_limit="0"  endpoint="http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/minio-dicom-upload" queue_dir=""
mc admin service restart jip
sleep 30s
mc event add jip/uploads/dicoms arn:minio:sqs::dicomsupload:webhook --event put --suffix .zip
