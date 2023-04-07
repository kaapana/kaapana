#!/bin/sh

sleep 30s
mc config host add kaapana http://minio-service.$SERVICES_NAMESPACE.svc:9000/ $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc mb kaapana/uploads
mc cp /kaapana/app/readme.txt kaapana/uploads/readme.txt
mc mb kaapana/staticwebsiteresults