#!/bin/bash
set -euf -o pipefail

echo 'Converting jupyter notebook file'
jupyter nbconvert --to pdf --no-input /executables/generate_nnunet_report/run_generate_nnunet_report.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR