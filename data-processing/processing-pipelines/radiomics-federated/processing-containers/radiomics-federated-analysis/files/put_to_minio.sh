#!/bin/bash
set -eu

MINIO_BUCKET="analysis-scripts"
mc alias set minio http://${MINIO_SERVICE} ${MINIO_USER} ${MINIO_PASSWORD}
mc mb --ignore-existing minio/${MINIO_BUCKET}

mc cp -r /files/analysis-scripts/ minio/${MINIO_BUCKET}