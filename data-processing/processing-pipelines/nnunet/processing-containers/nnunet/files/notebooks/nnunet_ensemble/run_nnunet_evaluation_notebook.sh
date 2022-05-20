#!/bin/bash
set -euf -o pipefail

echo 'Converting jupyter notebook file'
TIMESTAMP=$(date +%y-%m-%d-%H:%M:%S)
jupyter nbconvert --to pdf --execute --no-input /kaapanasrc/notebooks/nnunet_ensemble/run_nnunet_evaluation_notebook.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output nnunet_evaluation_${EXPERIMENT_NAME// /_}.pdf
jupyter nbconvert --to html --execute --no-input /kaapanasrc/notebooks/nnunet_ensemble/run_nnunet_evaluation_notebook.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output nnunet_evaluation_${EXPERIMENT_NAME// /_}.html