#!/bin/bash
set -eu

echo minio path: ${S3_PATH}

rclone_s3_args=(
    --s3-provider Other
    --s3-endpoint "http://${S3_SERVICE}"
    --s3-access-key-id "${S3_USER}"
    --s3-secret-access-key "${S3_PASSWORD}"
)

rclone mkdir "${rclone_s3_args[@]}" ":s3:/${S3_PATH}"

rclone copy "${rclone_s3_args[@]}" /files/analysis-scripts/ ":s3:/${S3_PATH}"
