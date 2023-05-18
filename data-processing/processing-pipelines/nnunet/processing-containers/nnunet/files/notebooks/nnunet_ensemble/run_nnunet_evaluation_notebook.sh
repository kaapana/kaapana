#!/bin/bash
set -euf -o pipefail

if [ ! -v WORKFLOW_NAME ]; then
    echo WORKFLOW_NAME not set, setting it to the RUN_ID
    WORKFLOW_NAME=$RUN_ID
    echo $WORKFLOW_NAME
fi

echo 'Converting jupyter notebook file'
TIMESTAMP=$(date +%y-%m-%d-%H:%M:%S)
jupyter nbconvert --to pdf --execute --no-input /kaapana/app/notebooks/nnunet_ensemble/run_nnunet_evaluation_notebook.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output nnunet_evaluation_${WORKFLOW_NAME// /_}.pdf
jupyter nbconvert --to html --execute --no-input /kaapana/app/notebooks/nnunet_ensemble/run_nnunet_evaluation_notebook.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output nnunet_evaluation_${WORKFLOW_NAME// /_}.html