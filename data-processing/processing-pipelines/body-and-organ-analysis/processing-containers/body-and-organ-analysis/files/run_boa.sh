IDENTIFIERS=$( jq -r '.data_form.identifiers[]' ${WORKFLOW_DIR}/conf/conf.json )

for SERIES_UID in $IDENTIFIERS; do
    python3 body_organ_analysis \
    --input-image ${BATCHES_INPUT_DIR}/${SERIES_UID}/${OPERATOR_IN_DIR}/${SERIES_UID}.nii.gz \
    --output-dir ${WORKFLOW_DIR}/${OPERATOR_OUT_DIR}/${SERIES_UID} \
    --models bca \
    --verbose
    
    python3 convert_nifti_to_dicom.py ${BATCHES_INPUT_DIR}/${SERIES_UID}/get-input-data ${WORKFLOW_DIR}/${OPERATOR_OUT_DIR}/${SERIES_UID}
done

