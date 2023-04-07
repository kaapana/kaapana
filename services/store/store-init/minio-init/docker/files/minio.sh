#!/bin/sh

sleep 30s
mc config host add kaapana http://minio-service.$SERVICES_NAMESPACE.svc:9000/ $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc mb --ignore-existing kaapana/uploads
mc mb --ignore-existing kaapana/staticwebsiteresults
mc cp /kaapana/app/readme.txt kaapana/uploads/readme.txt