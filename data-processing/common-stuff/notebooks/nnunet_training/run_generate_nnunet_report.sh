#!/bin/bash
set -euf -o pipefail

echo 'Converting jupyter notebook file'
TIMESTAMP=$(date +%y-%m-%d-%H:%M:%S)
jupyter nbconvert --to pdf --execute --no-input /common/notebooks/nnunet_training/run_generate_nnunet_report.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output run_generate_nnunet_report_$RUN_ID.pdf
jupyter nbconvert --to html --execute --no-input /common/notebooks/nnunet_training/run_generate_nnunet_report.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output run_generate_nnunet_report_$RUN_ID.html