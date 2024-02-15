#!/bin/bash
set -eu

MINIO_BUCKET="analysis-scripts"
mc alias set minio http://${MINIO_SERVICE} ${MINIO_USER} ${MINIO_PASSWORD}
mc cp -r minio/${MINIO_PATH} /files/analysis-scripts/

jupyter nbconvert --to html --execute --no-input /files/${MINIO_PATH}  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output $RUN_ID-report.html