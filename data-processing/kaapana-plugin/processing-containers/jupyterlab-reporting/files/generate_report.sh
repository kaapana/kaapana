#!/bin/bash
set -eu

IFS=',' read -ra FORMATS_ARRAY <<< "${OUTPUT_FORMAT}"
for format in "${FORMATS_ARRAY[@]}"; do
    jupyter nbconvert --to ${format} --execute --no-input /${WORKFLOW_DIR}/${NOTEBOOK_FILENAME}  --output-dir /${WORKFLOW_DIR}/${OPERATOR_OUT_DIR} --output ${RUN_ID}-report.${format}
done



