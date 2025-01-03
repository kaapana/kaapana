#!/bin/sh

sleep 30s
mc config host add kaapana http://minio-service.$SERVICES_NAMESPACE.svc:9000/ $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc mb --ignore-existing kaapana/uploads
mc mb --ignore-existing kaapana/staticwebsiteresults
mc mb --ignore-existing kaapana/template-analysis-scripts

mc admin policy create kaapana kaapanaUser /kaapana/app/user-policy.json