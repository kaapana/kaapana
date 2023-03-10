#!/bin/sh

sleep 30s
mc config host add kaapana http://minio-service.$SERVICES_NAMESPACE.svc:9000/ $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc admin user add kaapana landing landingminio
mc mb kaapana/uploads
mc cp readme_dicom.txt kaapana/uploads/dicoms/readme.txt
mc cp readme_itk.txt kaapana/uploads/itk/readme.txt
EVENT_LIST=$(mc event list kaapana/uploads | grep arn:minio:sqs::dicomsupload:webhook)
if [ "${EVENT_LIST%webhook*}" = "arn:minio:sqs::dicomsupload:" ]; then
    echo 'Event already set!'
    exit 0
fi

mc admin policy add kaapana putupload permissions_uploads.json
mc admin policy set kaapana putupload user=landing
mc admin config set kaapana notify_webhook:dicomsupload queue_limit="0"  endpoint="http://airflow-webserver-service.$SERVICES_NAMESPACE.svc:8080/flow/kaapana/api/trigger/service-minio-dicom-upload" queue_dir=""
mc admin config set kaapana notify_webhook:itkupload queue_limit="0"  endpoint="http://airflow-webserver-service.$SERVICES_NAMESPACE.svc:8080/flow/kaapana/api/trigger/dag-convert-nifti2dcm" queue_dir=""
mc admin service restart kaapana
sleep 30s
mc event add kaapana/uploads/dicoms arn:minio:sqs::dicomsupload:webhook --event put --suffix .zip
mc event add kaapana/uploads/itk arn:minio:sqs::itkupload:webhook --event put --suffix .zip