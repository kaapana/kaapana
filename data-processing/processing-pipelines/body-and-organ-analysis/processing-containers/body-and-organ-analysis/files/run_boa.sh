#!/bin/bash
IDENTIFIERS=$( jq -r '.data_form.identifiers[]' ${WORKFLOW_DIR}/conf/conf.json )
SELECTED_MODELS=$( jq -r '.workflow_form.models[]' ${WORKFLOW_DIR}/conf/conf.json )

TOTAL_SELECTED=false
for MODEL in $SELECTED_MODELS; do
    if [ "$MODEL" = "total" ]; then
        TOTAL_SELECTED=true
        break
    fi
done

if [ -n "$TOTAL_SELECTED" ]; then
    TOTAL_MODELS=$(jq -r '.workflow_form.total_models[]?' ${WORKFLOW_DIR}/conf/conf.json)
else
    TOTAL_MODELS=""
fi

ALL_MODELS="$SELECTED_MODELS $TOTAL_MODELS"
MODELS_ARGUMENT=$(echo ${ALL_MODELS} | sed 's/ /+/g')

for SERIES_UID in $IDENTIFIERS; do
    python3 body_organ_analysis \
    --input-image ${BATCHES_INPUT_DIR}/${SERIES_UID}/${OPERATOR_IN_DIR}/${SERIES_UID}.nii.gz \
    --output-dir ${WORKFLOW_DIR}/${OPERATOR_OUT_DIR}/${SERIES_UID} \
    --models ${MODELS_ARGUMENT} \
    --verbose
done

