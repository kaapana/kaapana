#! /bin/bash
set -eu -o pipefail

ROOT_INPUT_DICOM_DIR="/home/kaapana/dicom"
ROOT_OUTPUT_NRRD_DIR="/home/kaapana/nrrd"

for INPUT_DICOM_DIR in $( find ${ROOT_INPUT_DICOM_DIR} -mindepth 1 -maxdepth 1 -type d); do
    IDENTIFIER=$( basename ${INPUT_DICOM_DIR} )
    mkdir -p ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}
    /kaapana/app/apps/MitkFileConverter.sh -i ${INPUT_DICOM_DIR} -o ${ROOT_OUTPUT_NRRD_DIR}/${IDENTIFIER}/${IDENTIFIER}.nrrd
done