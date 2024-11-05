#!/bin/bash
set -eu

echo minio path: ${MINIO_PATH}

mc alias set minio http://${MINIO_SERVICE} ${MINIO_USER} ${MINIO_PASSWORD}
mc mb --ignore-existing minio/${MINIO_PATH}

mc cp -r /files/analysis-scripts/ minio/${MINIO_PATH}