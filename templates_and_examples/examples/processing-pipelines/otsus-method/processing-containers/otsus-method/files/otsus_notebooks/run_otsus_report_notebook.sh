#!/bin/bash
set -euf -o pipefail

if [ ! -v EXPERIMENT_NAME ]; then
    echo EXPERIMENT_NAME not set, setting it to the RUN_ID
    EXPERIMENT_NAME=$RUN_ID
    echo $EXPERIMENT_NAME
fi


echo 'Converting jupyter notebook file'
TIMESTAMP=$(date +%y-%m-%d-%H:%M:%S)
jupyter nbconvert --to pdf --execute --no-input /kaapanadevdata/otsus/run_otsus_report_notebook.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output nnunet_evaluation_${EXPERIMENT_NAME// /_}.pdf
jupyter nbconvert --to html --execute --no-input /kaapanadevdata/otsus/run_otsus_report_notebook.ipynb  --output-dir /$WORKFLOW_DIR/$OPERATOR_OUT_DIR --output nnunet_evaluation_${EXPERIMENT_NAME// /_}.html